import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CreateBorrowerPage from './page';

// 1. Mock Next.js navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: mockPush,
    }),
}));

describe('CreateBorrowerPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        global.fetch = vi.fn();
    });

    it('renders form inputs and submits successfully', async () => {
        const user = userEvent.setup();

        vi.spyOn(global, 'fetch').mockResolvedValueOnce({
            ok: true,
            json: async () => ({ id: 1, name: 'Alice Smith' }),
        } as Response);

        render(<CreateBorrowerPage />);

        // 1. Target the actual fields present in the form
        const nameInput = screen.getByLabelText(/name/i);
        const submitButton = screen.getByRole('button', { name: /save borrower/i });

        // 2. Perform user action
        await user.type(nameInput, 'Alice Smith');
        await user.click(submitButton);

        // 3. Verify fetch request payload
        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                expect.stringContaining('/borrowers'),
                expect.objectContaining({
                    method: 'POST',
                    headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
                    body: JSON.stringify({ name: 'Alice Smith' }),
                })
            );
        });

        // 4. Verify navigation
        expect(mockPush).toHaveBeenCalledWith('/');
    });

    it('logs the API error, does not redirect, and re-enables the submit button', async () => {
        const user = userEvent.setup();

        // 1. Spy on console.error and suppress terminal output during the test
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

        const errorPayload = { detail: 'Internal Server Error' };

        vi.spyOn(global, 'fetch').mockResolvedValueOnce({
            ok: false,
            status: 500,
            json: async () => errorPayload,
        } as Response);

        render(<CreateBorrowerPage />);

        const nameInput = screen.getByLabelText(/name/i);
        const submitButton = screen.getByRole('button', { name: /save borrower/i });

        await user.type(nameInput, 'Alice Smith');
        await user.click(submitButton);

        // 2. Assert console.error was called with the status and error body
        await waitFor(() => {
            expect(consoleSpy).toHaveBeenCalledWith('API Error (500):', errorPayload);
        });

        // 3. Assert no redirect happened
        expect(mockPush).not.toHaveBeenCalled();

        // 4. Assert button is active again (setIsSubmitting(false))
        expect(submitButton).toBeEnabled();

        // Clean up the spy
        consoleSpy.mockRestore();
    });
});