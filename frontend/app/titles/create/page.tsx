"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function CreateTitle() {
    const router = useRouter();
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        genre: ''
    });
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);

        // Generate a unique idempotency key in the background
        const idempotencyKey = crypto.randomUUID();

        try {
            const response = await fetch('/api/titles', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // Standard practice is to send idempotency keys in the header
                    'Idempotency-Key': idempotencyKey
                },
                body: JSON.stringify({
                    name: formData.name,
                    description: formData.description,
                    genre: formData.genre,
                    // Uncomment below if your Python backend expects the key in the payload instead of headers
                    // idempotency_key: idempotencyKey
                })
            });

            if (response.ok) {
                // Redirect back to the main page on success
                router.push('/');
            } else {
                // Extract the error details from the FastAPI response
                const errorData = await response.json().catch(() => ({}));
                console.error(`API Error (${response.status}):`, errorData);
                setIsSubmitting(false);
            }
        } catch (error) {
            console.error('API Error:', error);
            setIsSubmitting(false);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    return (
        <main className="p-8 max-w-md mx-auto">
            <h1 className="text-2xl font-bold mb-6">Add New Title</h1>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                <div>
                    <label className="block mb-1 font-medium" htmlFor="name">Name</label>
                    <input
                        type="text"
                        id="name"
                        name="name"
                        value={formData.name}
                        onChange={handleChange}
                        required
                        className="w-full border p-2 rounded text-black"
                    />
                </div>

                <div>
                    <label className="block mb-1 font-medium" htmlFor="description">Description</label>
                    <textarea
                        id="description"
                        name="description"
                        value={formData.description}
                        onChange={handleChange}
                        required
                        className="w-full border p-2 rounded text-black h-24"
                    />
                </div>

                <div>
                    <label className="block mb-1 font-medium" htmlFor="genre">Genre</label>
                    <input
                        type="text"
                        id="genre"
                        name="genre"
                        value={formData.genre}
                        onChange={handleChange}
                        required
                        className="w-full border p-2 rounded text-black"
                    />
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting}
                    className="mt-4 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                    {isSubmitting ? 'Saving...' : 'Save Title'}
                </button>
            </form>
        </main>
    );
}