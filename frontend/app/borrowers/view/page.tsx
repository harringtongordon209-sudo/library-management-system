"use client"; // This tells Next.js we want to use interactive browser features

import { useEffect, useState } from "react";

// This tells TypeScript what our data looks like (matches your FastAPI TitleSummary schema)
type Borrower = {
    borrower_id: string;
    name: string;
};

export default function Home() {
    // 1. Create a "state" variable to hold our borrowers. It starts as an empty array [].
    const [borrowers, setBorrowers] = useState<Borrower[]>([]);

    // 2. useEffect runs automatically as soon as the page loads on the screen.
    useEffect(() => {
        // 3. Make the exact same GET request your Swagger UI makes
        fetch("http://127.0.0.1:8000/api/borrowers")
            .then((response) => response.json()) // Convert the response to JSON
            .then((data) => setBorrowers(data))     // Save that data into our state variable
            .catch((error) => console.error("Error fetching data:", error));
    }, []);

    // 4. Draw the actual webpage
    return (
        <main className="p-10 bg-gray-100 min-h-screen text-gray-800">

            <div className="bg-white shadow rounded-lg p-6 max-w-2xl">
                <h2 className="text-2xl font-semibold mb-4 border-b pb-2">Borrowers List</h2>

                <ul className="space-y-3">
                    {/* 5. Loop through our borrowers and create a list item for each one */}
                    {borrowers.map((borrower) => (
                        <li key={borrower.borrower_id} className="p-3 bg-gray-50 border rounded-md shadow-sm">
                            <span className="font-medium">{borrower.name}</span>
                            <span className="text-xs text-gray-400 block mt-1">ID: {borrower.borrower_id}</span>
                        </li>
                    ))}

                    {/* If the database is empty, show a helpful message */}
                    {borrowers.length === 0 && (
                        <p className="text-gray-500 italic">No borrowers found. Add some first!</p>
                    )}
                </ul>
            </div>
        </main>
    );
}