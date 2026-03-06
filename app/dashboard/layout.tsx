import type { Metadata } from "next";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
    title: "Dashboard — ContextKeeper",
};

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex min-h-screen bg-black">
            <Sidebar />
            <main className="flex-1 ml-56 min-h-screen">
                {children}
            </main>
        </div>
    );
}
