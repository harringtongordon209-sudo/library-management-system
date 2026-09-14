"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

// Define the shape of your Title data based on your backend schemas

interface LibraryItem {
    id: string;
    name: string;
    barcode: string;
}

interface FormatItemsResponse {
    format_id: string;
    items: string[];
}

interface CheckoutResponse {
    checkout_id: string;
    startDate: string;
    dueDate: string;
    returnDate: string | null;
    item: LibraryItem;
}


interface Borrowers {
    borrower_id: string;
    name: string;
}

// Define the shape of your Title data based on your backend schemas
interface Title {
    title_id: string;
    name: string;
}

interface FormatInfo {
    format_id: string;
    format_type: string;
}

interface TitleFormatsResponse {
    title_id: string;
    name: string;
    format_types: FormatInfo[];
}

export default function CreateCheckoutPage() {
    const router = useRouter();

    const [borrowers, setBorrowers] = useState<Borrowers[]>([]);
    const [selectedBorrowerId, setSelectedBorrowerId] = useState("");
    const [titles, setTitles] = useState<Title[]>([]);
    const [selectedTitleId, setSelectedTitleId] = useState("");
    const [items, setItems] = useState<string[]>([]);
    const [selectedItemId, setSelectedItemId] = useState("");
    const [formats, setFormats] = useState<FormatInfo[]>([]);
    const [selectedFormatId, setSelectedFormatId] = useState("");

    const [createdCheckout, setCreatedCheckout] = useState<CheckoutResponse | null>(null);

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState("");

// Fetch available borrowers when the component mounts
    useEffect(() => {
        const fetchBorrowers = async () => {
            try {

                const response = await fetch("/api/borrowers");
                if (response.ok) {
                    const data = await response.json();
                    setBorrowers(data);
                } else {
                    console.error("Failed to fetch borrowers.");
                }
            } catch (err) {
                console.error("Error fetching borrowers:", err);
            }
        };
        fetchBorrowers();
    }, []);

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

    useEffect(() => {
        if (!selectedTitleId) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setFormats([]);
            return;
        }
        const fetchFormats = async () => {
            try {
                const response = await fetch(`/api/titles/${selectedTitleId}/formats`);
                if (response.ok) {
                    const data: TitleFormatsResponse = await response.json();
                    setFormats(data.format_types);
                } else {
                    console.error("Failed to fetch formats.");
                }
            } catch (err) {
                console.error("Error fetching formats:", err);
            }
        };
        fetchFormats();
    }, [selectedTitleId]);

    useEffect(() => {
        if (!selectedFormatId) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setItems([]);
            return;
        }
        const fetchItems = async () => {
            try {
                const response = await fetch(`/api/formats/${selectedFormatId}/items`);
                if (response.ok) {
                    const data: FormatItemsResponse = await response.json();
                    setItems(data.items);
                } else {
                    console.error("Failed to fetch items.");
                }
            } catch (err) {
                console.error("Error fetching itemss:", err);
            }
        };
        fetchItems();
    }, [selectedFormatId]);

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError("");
        setIsSubmitting(true);

        if (!selectedBorrowerId) {
            setError("Please select a borrower from the dropdown.");
            setIsSubmitting(false);
            return;
        }

        if (!selectedTitleId) {
            setError("Please select a title from the dropdown.");
            setIsSubmitting(false);
            return;
        }

        // Generate a new idempotency key for this specific submission
        const idempotencyKey = crypto.randomUUID();

        try {
            const response = await fetch(`/api/borrowers/${selectedBorrowerId}/checkoutRecords`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotencyKey,
                },
                body: JSON.stringify({
                    item: {id: selectedItemId},
                }),
            });

            if (response.ok) {
                const data: CheckoutResponse = await response.json();
                setCreatedCheckout(data);
            } else {
                const errData = await response.json();
                setError(errData.detail || "Failed to checkout item. Please try again.");
            }
        } catch (err) {
            setError("A network error occurred. Please check your connection.");
        } finally {
            setIsSubmitting(false);
        }
    };

    if (createdCheckout) {
        const borrowerName = borrowers.find(
            (b) => b.borrower_id === selectedBorrowerId
        )?.name || "Unknown Borrower";

        return (
            <main className="p-8 max-w-md mx-auto">
                <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
                    <h1 className="text-2xl font-bold text-green-700 mb-4">
                        Item Checked Out Successfully!
                    </h1>
                    <div className="space-y-3 mb-6">
                        <p>
                            <span className="font-semibold text-gray-700">Borrower:</span> {borrowerName}
                        </p>
                        <p>
                            <span className="font-semibold text-gray-700">Item:</span> {createdCheckout.item.name}
                        </p>
                        <p>
                            <span className="font-semibold text-gray-700">Barcode:</span> {createdCheckout.item.barcode}
                        </p>
                        <p>
                            <span className="font-semibold text-gray-700">Checkout Date:</span> {createdCheckout.startDate}
                        </p>
                        <p>
                            <span className="font-semibold text-gray-700">Due Date:</span> {createdCheckout.dueDate}
                        </p>
                    </div>
                    <div className="flex gap-4">
                        <button
                            type="button"
                            onClick={() => {
                                setCreatedCheckout(null);
                                setSelectedBorrowerId("");
                                setSelectedTitleId("");
                                setSelectedFormatId("");
                                setSelectedItemId("");
                            }}
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            Check Out Another Item
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
            </main>
        );
    }


    return (
        <main className="p-8 max-w-md mx-auto">
            <h1 className="text-2xl font-bold mb-6">Check Out an Item</h1>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                <div>
                    <label className="block mb-1 font-medium" htmlFor="borrower">Borrower</label>
                    <select
                        id="borrower"
                        name="borrower"
                        value={selectedBorrowerId}
                        onChange={(e) => setSelectedBorrowerId(e.target.value)}
                        required
                        className="w-full border p-2 rounded text-black"
                    >
                        <option value="">Select a borrower...</option>
                        {borrowers.map((borrower) => (
                            <option key={borrower.borrower_id} value={borrower.borrower_id}>
                                {borrower.name}
                            </option>
                        ))}
                    </select>
                </div>

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

                {selectedTitleId && (
                    <div>
                        <label className="block text-sm font-medium mb-1 text-gray-700">
                            Select Format
                        </label>
                        <select
                            value={selectedFormatId} onChange={(e) => setSelectedFormatId(e.target.value)}
                            className="w-full border border-gray-300 rounded-md p-2 focus:ring-blue-500 focus:border-blue-500"
                            required
                        >
                            <option value="" disabled>Select a format...</option>
                            {formats.map((t) => {
                                // Dynamically grab the correct ID and Name properties
                                const optionValue = t.format_id;
                                const optionLabel = t.format_type;

                                return (
                                    <option key={optionValue} value={optionValue}>
                                        {optionLabel}
                                    </option>
                                );
                            })}
                        </select>
                    </div>
                )}

                {selectedFormatId && (
                    <div>
                        <label className="block text-sm font-medium mb-1 text-gray-700">
                            Select Item
                        </label>
                        <select
                            value={selectedItemId} onChange={(e) => setSelectedItemId(e.target.value)}
                            className="w-full border border-gray-300 rounded-md p-2 focus:ring-blue-500 focus:border-blue-500"
                            required
                        >
                            <option value="" disabled>Select an item...</option>
                            {items.map((itemSerial) => (
                                <option key={itemSerial} value={itemSerial}>
                                    {itemSerial}
                                </option>
                            ))}
                        </select>
                    </div>
                )}

                {error && <p className="text-red-600 text-sm">{error}</p>}

                <button
                    type="submit"
                    disabled={isSubmitting || !selectedBorrowerId || !selectedItemId}
                    className="mt-4 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                    {isSubmitting ? 'Submitting...' : 'Check Out'}
                </button>
            </form>
        </main>
    );
}