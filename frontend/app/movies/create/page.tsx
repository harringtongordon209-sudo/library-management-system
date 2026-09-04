"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

// Define the shape of your Title data based on your backend schemas
interface Title {
    title_id: string;
    name: string;
}

interface MovieResponse {
    title_id: string;
    format_id: string;
    director: string;
    runtime: number;
    created_serial_numbers: string[];
}

export default function CreateMoviePage() {
    const router = useRouter();


    // Form State
    const [titles, setTitles] = useState<Title[]>([]);
    const [selectedTitleId, setSelectedTitleId] = useState("");
    const [director, setDirector] = useState("");
    const [runtime, setRuntime] = useState("");
    const [number_of_copies, setNumber_of_copies] = useState("");

    const [createdMovie, setCreatedMovie] = useState<MovieResponse | null>(null);

    // UI State
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState("");

    // Fetch available titles when the component mounts
    useEffect(() => {
        const fetchTitles = async () => {
            try {
                // Ensure this matches the actual endpoint where titles are served
                const response = await fetch("/api/titles");
                if (response.ok) {
                    const data = await response.json();
                    setTitles(data);
                } else {
                    console.error("Failed to fetch titles.");
                }
            } catch (err) {
                console.error("Error fetching titles:", err);
            }
        };
        fetchTitles();
    }, []);

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError("");
        setIsSubmitting(true);

        if (!selectedTitleId) {
            setError("Please select a title from the dropdown.");
            setIsSubmitting(false);
            return;
        }

        // Generate a new idempotency key for this specific submission
        const idempotencyKey = crypto.randomUUID();

        try {
            const response = await fetch(`/api/titles/${selectedTitleId}/Movie`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotencyKey,
                },
                body: JSON.stringify({
                    director: director, // Using "director" exactly as specified
                    runtime: parseInt(runtime, 10),
                    number_of_copies: parseInt(number_of_copies, 10),
                }),
            });

            if (response.ok) {
                const data: MovieResponse = await response.json();
                setCreatedMovie(data);
            } else {
                const errData = await response.json();
                setError(errData.message || "Failed to add the movie. Please try again.");
            }
        } catch (err) {
            setError("A network error occurred. Please check your connection.");
        } finally {
            setIsSubmitting(false);
        }
    };

    if (createdMovie) {
        const selectedTitle = titles.find(
            (t) => t.title_id === createdMovie.title_id
        );
        const titleName = selectedTitle?.name  || "Unknown Title";

        return (
            <div className="max-w-2xl mx-auto p-6">
                <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
                    <h1 className="text-2xl font-bold text-green-700 mb-4">
                        Movie Created Successfully!
                    </h1>
                    <div className="space-y-3 mb-6">
                        <p>
                            <span className="font-semibold text-gray-700">Title:</span> {titleName}
                        </p>
                        <p>
                            <span className="font-semibold text-gray-700">Director:</span> {createdMovie.director}
                        </p>
                        <p>
                            <span className="font-semibold text-gray-700">Runtime:</span> {createdMovie.runtime}
                        </p>
                        <div>
                            <span className="font-semibold text-gray-700">Created Items (Serial Numbers):</span>
                            <ul className="list-disc list-inside mt-2 bg-gray-50 border border-gray-200 rounded-md p-3 space-y-1 font-mono text-sm">
                                {createdMovie.created_serial_numbers.map((serial) => (
                                    <li key={serial}>{serial}</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                    <div className="flex gap-4">
                        <button
                            type="button"
                            onClick={() => {
                                setCreatedMovie(null);
                                setSelectedTitleId("");
                                setDirector("");
                                setRuntime("");
                                setNumber_of_copies((""))
                            }}
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            Add Another Movie
                        </button>
                        <button
                            type="button"
                            onClick={() => router.push("/")}
                            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100"
                        >
                            Return to Home
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-2xl mx-auto p-6">
            <h1 className="text-2xl font-bold mb-6">Add a New Movie</h1>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
                {/* Title Dropdown */}
                <div>
                    <label className="block text-sm font-medium mb-1 text-gray-700">
                        Select Title
                    </label>
                    <select
                        value={selectedTitleId}
                        onChange={(e) => setSelectedTitleId(e.target.value)}
                        className="w-full border border-gray-300 rounded-md p-2 focus:ring-blue-500 focus:border-blue-500"
                        required
                    >
                        <option value="" disabled>Select a title...</option>
                        {titles.map((t) => {
                            // Dynamically grab the correct ID and Name properties
                            const optionValue = t.title_id;
                            const optionLabel = t.name;

                            return (
                                <option key={optionValue} value={optionValue}>
                                    {optionLabel}
                                </option>
                            );
                        })}
                    </select>
                </div>

                {/* Director Input */}
                <div>
                    <label className="block text-sm font-medium mb-1 text-gray-700">
                        Director
                    </label>
                    <input
                        type="text"
                        value={director}
                        onChange={(e) => setDirector(e.target.value)}
                        className="w-full border border-gray-300 rounded-md p-2 focus:ring-blue-500 focus:border-blue-500"
                        required
                    />
                </div>

                {/* Runtime Input */}
                <div>
                    <label className="block text-sm font-medium mb-1 text-gray-700">
                        Runtime
                    </label>
                    <input
                        type="number"
                        value={runtime}
                        onChange={(e) => setRuntime(e.target.value)}
                        className="w-full border border-gray-300 rounded-md p-2 focus:ring-blue-500 focus:border-blue-500"
                        min="1"
                        required
                    />
                </div>

                {/* Number of Copies Input */}
                <div>
                    <label className="block text-sm font-medium mb-1 text-gray-700">
                        Number of Copies
                    </label>
                    <input
                        type="number"
                        value={number_of_copies}
                        onChange={(e) => setNumber_of_copies(e.target.value)}
                        className="w-full border border-gray-300 rounded-md p-2 focus:ring-blue-500 focus:border-blue-500"
                        min="1"
                        required
                    />
                </div>

                {/* Submit Button */}
                <div className="pt-4">
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full bg-blue-600 text-white font-medium px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isSubmitting ? "Saving..." : "Add Movie"}
                    </button>
                </div>
            </form>
        </div>
    );
}
