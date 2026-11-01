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

    it('renders the heading, an empty required name input, and an enabled submit button', () => {
        render(<CreateBorrowerPage />);

        expect(screen.getByRole('heading', { name: /add new borrower/i })).toBeInTheDocument();

        const nameInput = screen.getByLabelText(/name/i);
        expect(nameInput).toHaveValue('');
        expect(nameInput).toBeRequired();

        expect(screen.getByRole('button', { name: /save borrower/i })).toBeEnabled();
    });

    it('does not call the API when the required name field is empty', async () => {
        const user = userEvent.setup();

        render(<CreateBorrowerPage />);

        await user.click(screen.getByRole('button', { name: /save borrower/i }));

        expect(global.fetch).not.toHaveBeenCalled();
        expect(mockPush).not.toHaveBeenCalled();
    });

    it('POSTs to /api/borrowers with an Idempotency-Key header', async () => {
        const user = userEvent.setup();

        vi.spyOn(crypto, 'randomUUID').mockReturnValue('11111111-1111-1111-1111-111111111111');
        vi.spyOn(global, 'fetch').mockResolvedValueOnce({
            ok: true,
            json: async () => ({ id: 1, name: 'Alice Smith' }),
        } as Response);

        render(<CreateBorrowerPage />);

        await user.type(screen.getByLabelText(/name/i), 'Alice Smith');
        await user.click(screen.getByRole('button', { name: /save borrower/i }));

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                '/api/borrowers',
                expect.objectContaining({
                    headers: {
                        'Content-Type': 'application/json',
                        'Idempotency-Key': '11111111-1111-1111-1111-111111111111',
                    },
                })
            );
        });
    });

    it('shows "Saving..." and disables the button while the request is in flight', async () => {
        const user = userEvent.setup();

        let resolveFetch!: (value: Response) => void;
        vi.spyOn(global, 'fetch').mockReturnValueOnce(
            new Promise<Response>((resolve) => {
                resolveFetch = resolve;
            })
        );

        render(<CreateBorrowerPage />);

        await user.type(screen.getByLabelText(/name/i), 'Alice Smith');
        await user.click(screen.getByRole('button', { name: /save borrower/i }));

        const savingButton = await screen.findByRole('button', { name: /saving/i });
        expect(savingButton).toBeDisabled();
        expect(mockPush).not.toHaveBeenCalled();

        resolveFetch({ ok: true, json: async () => ({}) } as Response);

        await waitFor(() => {
            expect(mockPush).toHaveBeenCalledWith('/');
        });
    });

    it('logs the error, does not redirect, and re-enables the button when fetch rejects', async () => {
        const user = userEvent.setup();
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const networkError = new Error('Network down');

        vi.spyOn(global, 'fetch').mockRejectedValueOnce(networkError);

        render(<CreateBorrowerPage />);

        await user.type(screen.getByLabelText(/name/i), 'Alice Smith');
        await user.click(screen.getByRole('button', { name: /save borrower/i }));

        await waitFor(() => {
            expect(consoleSpy).toHaveBeenCalledWith('API Error:', networkError);
        });

        expect(mockPush).not.toHaveBeenCalled();
        expect(screen.getByRole('button', { name: /save borrower/i })).toBeEnabled();

        consoleSpy.mockRestore();
    });

    it('falls back to an empty object when the error response body is not valid JSON', async () => {
        const user = userEvent.setup();
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

        vi.spyOn(global, 'fetch').mockResolvedValueOnce({
            ok: false,
            status: 422,
            json: async () => {
                throw new SyntaxError('Unexpected token <');
            },
        } as unknown as Response);

        render(<CreateBorrowerPage />);

        await user.type(screen.getByLabelText(/name/i), 'Alice Smith');
        await user.click(screen.getByRole('button', { name: /save borrower/i }));

        await waitFor(() => {
            expect(consoleSpy).toHaveBeenCalledWith('API Error (422):', {});
        });

        expect(mockPush).not.toHaveBeenCalled();
        expect(screen.getByRole('button', { name: /save borrower/i })).toBeEnabled();

        consoleSpy.mockRestore();
    });

    it('generates a fresh Idempotency-Key for each submission attempt', async () => {
        const user = userEvent.setup();
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

        vi.spyOn(crypto, 'randomUUID')
            .mockReturnValueOnce('11111111-1111-1111-1111-111111111111')
            .mockReturnValueOnce('22222222-2222-2222-2222-222222222222');
        vi.spyOn(global, 'fetch')
            .mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({}) } as Response)
            .mockResolvedValueOnce({ ok: true, json: async () => ({}) } as Response);

        render(<CreateBorrowerPage />);

        await user.type(screen.getByLabelText(/name/i), 'Alice Smith');

        // First attempt fails, button re-enables, user retries
        await user.click(screen.getByRole('button', { name: /save borrower/i }));
        await waitFor(() => expect(consoleSpy).toHaveBeenCalled());
        await waitFor(() => expect(screen.getByRole('button', { name: /save borrower/i })).toBeEnabled());
        await user.click(screen.getByRole('button', { name: /save borrower/i }));

        await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));

        const calls = vi.mocked(global.fetch).mock.calls;
        const keys = calls.map(([, init]) => (init?.headers as Record<string, string>)['Idempotency-Key']);
        expect(keys).toEqual([
            '11111111-1111-1111-1111-111111111111',
            '22222222-2222-2222-2222-222222222222',
        ]);

        consoleSpy.mockRestore();
    });

    it('sends whitespace-only names as-is (no trimming)', async () => {
        const user = userEvent.setup();

        vi.spyOn(global, 'fetch').mockResolvedValueOnce({
            ok: true,
            json: async () => ({}),
        } as Response);

        render(<CreateBorrowerPage />);

        await user.type(screen.getByLabelText(/name/i), '   ');
        await user.click(screen.getByRole('button', { name: /save borrower/i }));

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                '/api/borrowers',
                expect.objectContaining({ body: JSON.stringify({ name: '   ' }) })
            );
        });
    });
});