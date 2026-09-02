"use client"; // This tells Next.js we want to use interactive browser features

import { useEffect, useState } from "react";
import Link from "next/link";

// This tells TypeScript what our data looks like (matches your FastAPI TitleSummary schema)
type Title = {
  title_id: string;
  name: string;
};

export default function Home() {
    return (
        <main className="p-8">
            <h1 className="text-2xl font-bold mb-6">Library Management System</h1>

            <div className="flex flex-col gap-6">

                {/* Titles Section */}
                <div className="flex flex-row items-center gap-4">
                    <Link
                        href="/titles/view"
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 inline-block font-medium"
                    >
                        View Titles
                    </Link>
                    <Link
                        href="/titles/create"
                        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 inline-block font-medium"
                    >
                        Create New Title
                    </Link>
                    <Link
                        href="/books/create"
                        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 inline-block font-medium"
                    >
                        Create New Book
                    </Link>
                </div>

                {/* Borrowers Section */}
                <div className="flex flex-row items-center gap-4">
                    <Link
                        href="/borrowers/view"
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 inline-block font-medium"
                    >
                        View Borrowers
                    </Link>
                    <Link
                        href="/borrowers/create"
                        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 inline-block font-medium"
                    >
                        Create New Borrower
                    </Link>
                </div>

            </div>
        </main>

    );
}
