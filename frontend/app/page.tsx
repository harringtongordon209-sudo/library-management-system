"use client"; // This tells Next.js we want to use interactive browser features

import { useEffect, useState } from "react";

// This tells TypeScript what our data looks like (matches your FastAPI TitleSummary schema)
type Title = {
  title_id: string;
  name: string;
};

export default function Home() {
  // 1. Create a "state" variable to hold our books. It starts as an empty array [].
  const [titles, setTitles] = useState<Title[]>([]);

  // 2. useEffect runs automatically as soon as the page loads on the screen.
  useEffect(() => {
    // 3. Make the exact same GET request your Swagger UI makes
    fetch("http://127.0.0.1:8000/api/titles")
        .then((response) => response.json()) // Convert the response to JSON
        .then((data) => setTitles(data))     // Save that data into our state variable
        .catch((error) => console.error("Error fetching data:", error));
  }, []);

  // 4. Draw the actual webpage
  return (
      <main className="p-10 bg-gray-100 min-h-screen text-gray-800">
        <h1 className="text-4xl font-bold text-blue-600 mb-8">Welcome to the Library System</h1>

        <div className="bg-white shadow rounded-lg p-6 max-w-2xl">
          <h2 className="text-2xl font-semibold mb-4 border-b pb-2">Library Catalog</h2>

          <ul className="space-y-3">
            {/* 5. Loop through our titles and create a list item for each one */}
            {titles.map((title) => (
                <li key={title.title_id} className="p-3 bg-gray-50 border rounded-md shadow-sm">
                  <span className="font-medium">{title.name}</span>
                  <span className="text-xs text-gray-400 block mt-1">ID: {title.title_id}</span>
                </li>
            ))}

            {/* If the database is empty, show a helpful message */}
            {titles.length === 0 && (
                <p className="text-gray-500 italic">No books found. Add some via Swagger!</p>
            )}
          </ul>
        </div>
      </main>
  );
}
