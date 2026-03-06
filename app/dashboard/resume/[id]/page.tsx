"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import {
    ArrowLeft,
    Clock,
    CheckCircle,
    Circle,
    FileCode,
    Terminal,
    Tag,
    Loader2,
    Zap,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// ─── dev / demo mock data ─────────────────────────────────────────────────────
// Used as a fallback when the backend is unreachable (local dev, demo mode).
const MOCK_SNAPSHOTS: Record<string, Snapshot> = {
    "snap-001": {
        id: "snap-001",
        name: "JWT Auth Refactor",
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        project_path: "/projects/myapp/backend",
        active_file: "backend/auth/auth.service.ts",
        ai_summary:
            "You were refactoring the JWT authentication service in auth.service.ts, specifically fixing the token expiry validation bug on line 142. You had just extracted the token validation logic into a reusable helper function, reducing the auth middleware from 85 to 42 lines.",
        next_steps: [
            "Add unit test for validateToken() at line 142",
            "Update the refresh token endpoint to use the new validateToken helper",
            "Deploy auth service to staging and run smoke tests",
        ],
        tags: ["auth", "backend", "refactor"],
        open_files: [
            { path: "backend/auth/auth.service.ts", cursor_line: 142 },
            { path: "backend/auth/jwt.util.ts", cursor_line: 34 },
            { path: "backend/controllers/PaymentController.ts", cursor_line: 28 },
            { path: "backend/services/PaymentService.ts", cursor_line: 61 },
        ],
        recent_edits: [
            { file: "auth.service.ts", line: 142, timestamp: "2h ago" },
            { file: "jwt.util.ts", line: 34, timestamp: "2h 15m ago" },
            { file: "auth.service.ts", line: 85, timestamp: "2h 45m ago" },
        ],
        terminal_commands: [
            "npm run test:unit",
            "git diff HEAD~1 --stat",
            "npx jest auth.service.spec.ts",
        ],
        time_spent_minutes: 87,
    },
};

const DEFAULT_MOCK: Snapshot = {
    id: "snap-unknown",
    name: "Saved Checkpoint",
    timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    project_path: "/projects/myapp",
    active_file: "src/main.ts",
    ai_summary:
        "You were working on a feature implementation. Your context has been saved and you can resume where you left off.",
    next_steps: [
        "Review the changes you were working on",
        "Run the test suite to check for regressions",
        "Continue with the next task on your list",
    ],
    tags: ["development"],
    open_files: [{ path: "src/main.ts", cursor_line: 1 }],
    recent_edits: [],
    terminal_commands: [],
    time_spent_minutes: 60,
};

function timeAgo(ts: string): string {
    const diff = Date.now() - new Date(ts).getTime();
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    if (h > 0) return `${h}h ${m}m ago`;
    return `${m}m ago`;
}

// ─── types ────────────────────────────────────────────────────────────────────

interface OpenFile {
    path: string;
    cursor_line: number;
}

interface RecentEdit {
    file: string;
    line: number;
    timestamp: string;
}

interface Snapshot {
    id: string;
    name: string;
    timestamp: string;
    project_path: string;
    active_file: string;
    ai_summary: string;
    next_steps: string[];
    tags: string[];
    open_files: OpenFile[];
    recent_edits: RecentEdit[];
    terminal_commands: string[];
    time_spent_minutes: number;
}

// ─── component ────────────────────────────────────────────────────────────────

export default function ResumePage({
    params,
}: {
    // In the App Router params is a plain object, NOT a Promise.
    params: { id: string };
}) {
    const { id } = params;

    const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
    const [loadingSnapshot, setLoadingSnapshot] = useState(true);
    const [checkedSteps, setCheckedSteps] = useState<boolean[]>([]);
    const [showBriefing, setShowBriefing] = useState(false);
    const [loadingBriefing, setLoadingBriefing] = useState(false);
    const [briefing, setBriefing] = useState<string | null>(null);

    useEffect(() => {
        async function fetchSnapshot() {
            // If no API URL is configured, skip the network call entirely.
            if (!API_URL) {
                const mock = MOCK_SNAPSHOTS[id] ?? DEFAULT_MOCK;
                setSnapshot(mock);
                setCheckedSteps(new Array(mock.next_steps.length).fill(false));
                setLoadingSnapshot(false);
                return;
            }
            try {
                const res = await fetch(`${API_URL}/snapshots/${id}`);
                if (res.ok) {
                    const data: Snapshot = await res.json();
                    setSnapshot(data);
                    setCheckedSteps(new Array(data.next_steps?.length ?? 0).fill(false));
                } else {
                    // API reachable but snapshot not found — fall back to mock.
                    console.warn(`API returned ${res.status} for snapshot ${id}, using mock data.`);
                    const mock = MOCK_SNAPSHOTS[id] ?? DEFAULT_MOCK;
                    setSnapshot(mock);
                    setCheckedSteps(new Array(mock.next_steps.length).fill(false));
                }
            } catch (err) {
                // Network error (backend down, CORS, etc.) — fall back to mock.
                console.warn("Failed to fetch snapshot, using mock data:", err);
                const mock = MOCK_SNAPSHOTS[id] ?? DEFAULT_MOCK;
                setSnapshot(mock);
                setCheckedSteps(new Array(mock.next_steps.length).fill(false));
            } finally {
                setLoadingSnapshot(false);
            }
        }
        fetchSnapshot();
    }, [id]);

    const toggleStep = (i: number) => {
        const next = [...checkedSteps];
        next[i] = !next[i];
        setCheckedSteps(next);
    };

    const handleGetBriefing = async () => {
        setLoadingBriefing(true);
        setShowBriefing(true);
        if (!API_URL) {
            // No backend — generate a mock briefing from the snapshot data.
            setTimeout(() => {
                setBriefing(
                    `Welcome back! You were working on "${snapshot?.name}". ` +
                    `${snapshot?.ai_summary} ` +
                    `Your next step is: ${snapshot?.next_steps?.[0] ?? "review your recent changes"}.`
                );
                setLoadingBriefing(false);
            }, 800);
            return;
        }
        try {
            const res = await fetch(`${API_URL}/snapshots/${id}/resume`);
            if (res.ok) {
                const data = await res.json();
                setBriefing(data.briefing);
            } else {
                setBriefing("Could not generate AI briefing at this time.");
            }
        } catch (err) {
            console.error("Briefing error", err);
            setBriefing("There was an error generating the briefing.");
        } finally {
            setLoadingBriefing(false);
        }
    };

    if (loadingSnapshot) {
        return (
            <div className="p-12 flex justify-center items-center text-zinc-500">
                <Loader2 size={24} className="animate-spin" />
            </div>
        );
    }

    if (!snapshot) {
        return (
            <div className="p-12 text-center space-y-4">
                <p className="text-zinc-500 font-mono">Snapshot not found.</p>
                <Link href="/dashboard" className="text-xs text-blue-400 hover:underline">
                    Back to Dashboard
                </Link>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-4xl mx-auto space-y-6 animate-in">
            {/* Back */}
            <div className="pt-2">
                <Link
                    href="/dashboard"
                    className="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-600 hover:text-zinc-300 transition-colors mb-4"
                >
                    <ArrowLeft size={12} />
                    Back to Dashboard
                </Link>

                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">{snapshot.name}</h1>
                        <div className="flex items-center gap-3 mt-1">
                            <span className="text-xs font-mono text-zinc-600 flex items-center gap-1">
                                <Clock size={11} /> Saved {timeAgo(snapshot.timestamp)}
                            </span>
                            <span className="text-xs font-mono text-zinc-600 flex items-center gap-1">
                                <Zap size={11} /> {snapshot.time_spent_minutes}m session
                            </span>
                        </div>
                    </div>
                    <button
                        onClick={handleGetBriefing}
                        disabled={loadingBriefing}
                        className="flex items-center gap-2 bg-white text-black text-sm font-semibold px-4 py-2 rounded hover:bg-zinc-200 disabled:opacity-50 transition-all flex-shrink-0"
                    >
                        {loadingBriefing ? (
                            <Loader2 size={14} className="animate-spin" />
                        ) : (
                            "🧠"
                        )}
                        AI Re-Orient Me
                    </button>
                </div>
            </div>

            {/* AI Briefing */}
            {showBriefing && (
                <div className="border border-blue-900/30 bg-blue-950/10 rounded-xl p-5 animate-in">
                    <p className="text-[10px] uppercase tracking-widest font-mono text-blue-500/60 mb-2.5">
                        AI Re-Orientation Briefing
                    </p>
                    {loadingBriefing ? (
                        <div className="flex items-center gap-2 text-zinc-500">
                            <Loader2 size={14} className="animate-spin" />
                            <span className="text-sm font-mono">Generating briefing...</span>
                        </div>
                    ) : (
                        <p className="text-sm text-zinc-300 leading-relaxed">{briefing}</p>
                    )}
                </div>
            )}

            {/* AI Summary */}
            <div className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-5">
                <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-3">
                    Last Context Summary
                </p>
                <p className="text-sm text-zinc-300 leading-relaxed border-l-2 border-zinc-700 pl-3">
                    {snapshot.ai_summary}
                </p>

                {/* Tags */}
                {snapshot.tags && (
                    <div className="flex items-center gap-1.5 mt-3 flex-wrap">
                        <Tag size={10} className="text-zinc-700" />
                        {snapshot.tags.map((tag: string) => (
                            <span
                                key={tag}
                                className="text-[10px] font-mono bg-zinc-900 border border-zinc-800 text-zinc-500 px-1.5 py-0.5 rounded-sm"
                            >
                                {tag}
                            </span>
                        ))}
                    </div>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Next Steps — Checklist */}
                <div className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-5">
                    <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-3">
                        Next Steps
                    </p>
                    <div className="space-y-2.5">
                        {snapshot.next_steps.map((step: string, i: number) => (
                            <button
                                key={i}
                                onClick={() => toggleStep(i)}
                                className="w-full flex items-start gap-2.5 text-left group"
                            >
                                {checkedSteps[i] ? (
                                    <CheckCircle
                                        size={15}
                                        className="text-emerald-500 mt-0.5 flex-shrink-0"
                                    />
                                ) : (
                                    <Circle
                                        size={15}
                                        className="text-zinc-700 mt-0.5 flex-shrink-0 group-hover:text-zinc-500 transition-colors"
                                    />
                                )}
                                <span
                                    className={`text-sm font-mono transition-colors ${checkedSteps[i]
                                        ? "line-through text-zinc-600"
                                        : "text-zinc-300 group-hover:text-white"
                                        }`}
                                >
                                    {step}
                                </span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Open Files */}
                <div className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-5">
                    <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-3">
                        Open Files
                    </p>
                    <div className="space-y-2">
                        {snapshot.open_files?.map((f: OpenFile, i: number) => (
                            <div
                                key={i}
                                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 transition-all ${i === 0
                                    ? "border border-[#333] bg-[#111]"
                                    : "border border-transparent hover:border-[#1a1a1a]"
                                    }`}
                            >
                                <FileCode
                                    size={12}
                                    className={i === 0 ? "text-white" : "text-zinc-600"}
                                />
                                <div className="min-w-0 flex-1">
                                    <p
                                        className={`text-xs font-mono truncate ${i === 0 ? "text-white" : "text-zinc-500"
                                            }`}
                                    >
                                        {f.path.split("/").pop()}
                                    </p>
                                    <p className="text-[10px] text-zinc-700 font-mono truncate">
                                        {f.path}
                                    </p>
                                </div>
                                {f.cursor_line > 0 && (
                                    <span className="text-[10px] font-mono text-zinc-700 flex-shrink-0">
                                        L{f.cursor_line}
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Recent Edits + Terminal */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {snapshot.recent_edits && snapshot.recent_edits.length > 0 && (
                    <div className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-5">
                        <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-3">
                            Recent Edits
                        </p>
                        <div className="space-y-2">
                            {snapshot.recent_edits.map((edit: RecentEdit, i: number) => (
                                <div
                                    key={i}
                                    className="flex items-center gap-2 text-xs font-mono text-zinc-500"
                                >
                                    <span className="text-zinc-700">~</span>
                                    <span className="text-zinc-400 truncate">{edit.file}</span>
                                    <span className="text-zinc-700 flex-shrink-0">
                                        L{edit.line}
                                    </span>
                                    <span className="text-zinc-700 ml-auto flex-shrink-0">
                                        {edit.timestamp}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {snapshot.terminal_commands && snapshot.terminal_commands.length > 0 && (
                    <div className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-5">
                        <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-3 flex items-center gap-1.5">
                            <Terminal size={10} />
                            Recent Commands
                        </p>
                        <div className="space-y-1.5">
                            {snapshot.terminal_commands.map((cmd: string, i: number) => (
                                <div key={i} className="flex items-center gap-2 text-xs font-mono">
                                    <span className="text-zinc-700">$</span>
                                    <span className="text-zinc-400">{cmd}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}