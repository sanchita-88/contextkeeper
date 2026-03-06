"use client";
import { useState, useEffect } from "react";
import SnapshotCard from "@/components/SnapshotCard";
import { API_URL } from "@/lib/config";
import {
    Bookmark,
    Database,
    Zap,
    TrendingUp,
    Plus,
    Bell,
    Loader2
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
    const [snapshots, setSnapshots] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>("all");

    useEffect(() => {
        async function fetchSnapshots() {
            try {
                const res = await fetch(`${API_URL}/snapshots`);
                if (res.ok) {
                    const data = await res.json();
                    setSnapshots(data);
                }
            } catch (err) {
                console.error("Failed to fetch snapshots", err);
            } finally {
                setLoading(false);
            }
        }
        fetchSnapshots();
    }, []);

    const allTags = Array.from(new Set(snapshots.flatMap((s) => s.tags || [])));

    const filtered =
        filter === "all"
            ? snapshots
            : snapshots.filter((s) => (s.tags || []).includes(filter));

    const todayDate = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    const nowTime = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });

    const stats = [
        { icon: Bookmark, label: "Snapshots Saved", value: loading ? "..." : snapshots.length.toString(), change: "Total tracked" },
        { icon: Database, label: "Repos Indexed", value: loading ? "..." : (new Set(snapshots.map(s => s.project_path)).size).toString(), change: "Active projects" },
        { icon: Zap, label: "Focus Hrs Saved", value: "0h", change: "Feature WIP" },
        { icon: TrendingUp, label: "Interruptions Deferred", value: "0", change: "Feature WIP" },
    ];

    return (
        <div className="p-6 max-w-5xl mx-auto space-y-8 animate-in">
            {/* Header */}
            <div className="flex items-center justify-between pt-2">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
                    <p className="text-sm text-zinc-500 mt-0.5 font-mono">
                        {todayDate} · {nowTime}
                    </p>
                </div>
                <Link
                    href="/dashboard/checkpoint"
                    className="flex items-center gap-1.5 bg-white text-black text-xs font-semibold px-3 py-2 rounded hover:bg-zinc-200 transition-all"
                >
                    <Plus size={13} strokeWidth={2.5} />
                    New Checkpoint
                </Link>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {stats.map(({ icon: Icon, label, value, change }) => (
                    <div
                        key={label}
                        className="border border-[#1a1a1a] bg-[#050505] rounded-lg p-4"
                    >
                        <div className="flex items-center gap-2 mb-3">
                            <Icon size={13} className="text-zinc-600" />
                            <span className="text-[10px] uppercase tracking-widest text-zinc-600 font-mono">
                                {label}
                            </span>
                        </div>
                        <div className="text-2xl font-bold font-mono">{value}</div>
                        <div className="text-[11px] text-zinc-600 mt-1">{change}</div>
                    </div>
                ))}
            </div>

            {/* Notification Banner */}
            <div className="flex items-center gap-3 border border-yellow-900/40 bg-yellow-950/10 rounded-lg px-4 py-3">
                <Bell size={14} className="text-yellow-500 flex-shrink-0" />
                <p className="text-xs text-yellow-400/80">
                    <span className="font-semibold text-yellow-400">Focus Shield active.</span>{" "}
                    Configure auto-defer routing via the Interruptions panel {" "}
                    <Link href="/dashboard/interruptions" className="underline hover:text-yellow-300 transition-colors">
                        Review them →
                    </Link>
                </p>
            </div>

            {/* Context Snapshots */}
            <div>
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h2 className="text-sm font-semibold">Context Snapshots</h2>
                        <p className="text-xs text-zinc-600 font-mono mt-0.5">
                            {loading ? "Loading..." : `${snapshots.length} saved · click a card to resume`}
                        </p>
                    </div>

                    {/* Tag Filter */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                        <button
                            onClick={() => setFilter("all")}
                            className={`text-[10px] font-mono px-2 py-1 rounded-sm border transition-all ${filter === "all"
                                ? "bg-white text-black border-white"
                                : "border-[#222] text-zinc-500 hover:border-[#444] hover:text-zinc-300"
                                }`}
                        >
                            all
                        </button>
                        {allTags.map((tag) => (
                            <button
                                key={tag}
                                onClick={() => setFilter(tag)}
                                className={`text-[10px] font-mono px-2 py-1 rounded-sm border transition-all ${filter === tag
                                    ? "bg-white text-black border-white"
                                    : "border-[#222] text-zinc-500 hover:border-[#444] hover:text-zinc-300"
                                    }`}
                            >
                                {tag}
                            </button>
                        ))}
                    </div>
                </div>

                {loading ? (
                    <div className="flex justify-center items-center py-12 text-zinc-500">
                        <Loader2 size={16} className="animate-spin mr-2" />
                        <span className="text-sm font-mono">Fetching snapshots...</span>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {filtered.map((snap) => (
                            <SnapshotCard key={snap.id} snapshot={snap} />
                        ))}
                    </div>
                )}

                {!loading && filtered.length === 0 && (
                    <div className="border border-[#1a1a1a] rounded-lg p-8 text-center bg-[#050505]">
                        <p className="text-sm text-zinc-600 font-mono mb-2">
                            {snapshots.length === 0 ? "No snapshots found in database." : `No snapshots with tag "${filter}"`}
                        </p>
                        {snapshots.length === 0 && (
                            <Link href="/dashboard/checkpoint" className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
                                + Create your first checkpoint
                            </Link>
                        )}
                    </div>
                )}
            </div>

            {/* Quick Actions */}
            <div>
                <h2 className="text-sm font-semibold mb-3">Quick Actions</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {[
                        {
                            href: "/dashboard/codebase",
                            title: "Query Codebase",
                            desc: "Ask a question about your indexed repos",
                            icon: Database,
                        },
                        {
                            href: "/dashboard/diagram",
                            title: "Generate Diagram",
                            desc: "Create architecture diagrams from code",
                            icon: Zap,
                        },
                        {
                            href: "/dashboard/interruptions",
                            title: "Focus Shield",
                            desc: "Classify and defer incoming interruptions",
                            icon: Bell,
                        },
                    ].map(({ href, title, desc, icon: Icon }) => (
                        <Link
                            key={href}
                            href={href}
                            className="border border-[#1a1a1a] bg-[#050505] hover:border-[#333] rounded-lg p-4 transition-all group"
                        >
                            <Icon size={15} className="text-zinc-500 mb-3 group-hover:text-zinc-300 transition-colors" />
                            <p className="text-sm font-medium mb-1">{title}</p>
                            <p className="text-xs text-zinc-600">{desc}</p>
                        </Link>
                    ))}
                </div>
            </div>
        </div>
    );
}
