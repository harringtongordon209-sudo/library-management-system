"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

interface Borrowers {
    borrower_id: string;
    name: string;
}

interface LibraryItem {
    id: string;
    name: string;
    barcode: string;
}

interface CheckoutRecords {
    checkout_id: string;
    startDate: string;
    dueDate: string;
    returnDate: string | null;
    item: LibraryItem;
}


export default function CreateCheckInPage() {
    const router = useRouter();
    const [borrowers, setBorrowers] = useState<Borrowers[]>([]);
    const [checkoutRecords, setCheckoutRecords] = useState<CheckoutRecords[]>([]);
    const [selectedCheckoutRecord, setSelectedCheckoutRecord] = useState("");
    const [selectedBorrowerId, setSelectedBorrowerId] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState("");
    const [createdCheckin, setCreatedCheckin] = useState<CheckoutRecords | null>(null);


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

    useEffect(() => {
        if (!selectedBorrowerId) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setCheckoutRecords([]);
            return;
        }
        const fetchCheckoutRecords = async () => {
            try {

                const response = await fetch(`/api/borrowers/${selectedBorrowerId}/checkoutRecords`);
                if (response.ok) {
                    const data = await response.json();
                    setCheckoutRecords(data);
                } else {
                    console.error("Failed to fetch checkout records.");
                }
            } catch (err) {
                console.error("Error fetching checkout records:", err);
            }
        };
        fetchCheckoutRecords();
    }, [selectedBorrowerId]);

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError("");
        setIsSubmitting(true);

        if (!selectedBorrowerId) {
            setError("Please select a borrower from the dropdown.");
            setIsSubmitting(false);
            return;
        }

        if (!selectedCheckoutRecord) {
            setError("Please select a checkout record from the dropdown.");
            setIsSubmitting(false);
            return;
        }

        try {
            const response = await fetch(`/api/borrowers/${selectedBorrowerId}/checkoutRecords/${selectedCheckoutRecord}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                }),
            });

            if (response.ok) {
                const data: CheckoutRecords = await response.json();
                setCreatedCheckin(data);
            } else {
                const errData = await response.json();
                setError(errData.detail || "Failed to checkin item. Please try again.");
            }
        } catch (err) {
            setError("A network error occurred. Please check your connection.");
        } finally {
            setIsSubmitting(false);
        }
    };

    if (createdCheckin) {
        const borrowerName = borrowers.find(
            (b) => b.borrower_id === selectedBorrowerId
        )?.name || "Unknown Borrower";

        return (
            <main className="p-8 max-w-md mx-auto">
                <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
                    <h1 className="text-2xl font-bold text-green-700 mb-4">
                        Item Checked In Successfully!
                    </h1>
                    <div className="space-y-3 mb-6">
                        <p>
                            <span className="font-semibold text-gray-700">Borrower:</span> {borrowerName}
                        </p>
                        <p>
                            <span className="font-semibold text-gray-700">Item:</span> {createdCheckin.item.name}
                        </p>
                        <p>
                            <span className="font-semibold text-gray-700">Barcode:</span> {createdCheckin.item.barcode}
                        </p>
                        <p>
                            <span className="font-semibold text-gray-700">Checkout Date:</span> {createdCheckin.startDate}
                        </p>
                        <p>
                            <span className="font-semibold text-gray-700">Due Date:</span> {createdCheckin.dueDate}
                        </p>
                    </div>
                    <div className="flex gap-4">
                        <button
                            type="button"
                            onClick={() => {
                                setCreatedCheckin(null);
                                setSelectedBorrowerId("");
                                setSelectedCheckoutRecord("");
                            }}
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            Check In Another Item
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
            <h1 className="text-2xl font-bold mb-6">Check In an Item</h1>

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

                {selectedBorrowerId && (
                    <div>
                        <label className="block text-sm font-medium mb-1 text-gray-700">
                            Select Checkout Record to Check In
                        </label>
                        <select
                            value={selectedCheckoutRecord} onChange={(e) => setSelectedCheckoutRecord(e.target.value)}
                            className="w-full border border-gray-300 rounded-md p-2 focus:ring-blue-500 focus:border-blue-500"
                            required
                        >
                            <option value="" disabled>Select a checkout record...</option>
                            {checkoutRecords.map((checkoutRecord) => (
                                <option key={checkoutRecord.checkout_id} value={checkoutRecord.checkout_id}>
                                    {`${checkoutRecord.item.name} (Barcode: ${checkoutRecord.item.barcode}) - Due: ${checkoutRecord.dueDate}`}
                                </option>
                            ))}
                        </select>
                    </div>
                )}

                {error && <p className="text-red-600 text-sm">{error}</p>}

                <button
                    type="submit"
                    disabled={isSubmitting || !selectedBorrowerId || !selectedCheckoutRecord}
                    className="mt-4 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                    {isSubmitting ? 'Submitting...' : 'Check In'}
                </button>
            </form>
        </main>
    );

}