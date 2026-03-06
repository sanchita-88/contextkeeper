"use client";
import { useState, useEffect } from "react";
import { Zap, Loader2, Clock, MessageSquare } from "lucide-react";
import PriorityBadge from "@/components/PriorityBadge";
import { API_URL } from "@/lib/config";

const SOURCES = [
    { value: "slack", label: "Slack" },
    { value: "code_review", label: "Code Review" },
    { value: "production", label: "Production Alert" },
    { value: "meeting", label: "Meeting Request" },
    { value: "other", label: "Other" },
];

const EXAMPLES = [
    { msg: "Can you quickly review my PR? It's minor.", source: "slack" },
    { msg: "PRODUCTION DOWN! Payment service is returning 500s for all users", source: "production" },
    { msg: "Hey, do you have 5 min for a quick sync about Q2 roadmap?", source: "meeting" },
];

type InterruptionResult = {
    priority: "critical" | "important" | "deferrable";
    reason: string;
    auto_reply: string;
    defer_duration_minutes: number;
    action_required: string;
};

type LogEntry = {
    id: number | string;
    timestamp: string;
    source: string;
    message: string;
    priority: "critical" | "important" | "deferrable";
    auto_reply?: string;
};

export default function InterruptionsPage() {
    const [message, setMessage] = useState("");
    const [source, setSource] = useState("slack");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<InterruptionResult | null>(null);
    const [log, setLog] = useState<LogEntry[]>([]);

    useEffect(() => {
        async function fetchLog() {
            try {
                const res = await fetch(`${API_URL}/interruptions`);
                if (res.ok) {
                    const data = await res.json();
                    setLog(data);
                }
            } catch (err) {
                console.error("Failed to fetch interruptions log", err);
            }
        }
        fetchLog();
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setResult(null);

        try {
            const res = await fetch(`${API_URL}/interruptions/classify`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message,
                    source,
                    current_context: "Focus mode activated in dashboard"
                }),
            });

            if (!res.ok) throw new Error("Classification failed");

            const data = await res.json();
            setResult(data);

            // Unshift new classification into log instantly
            const newLogEntry = {
                id: Date.now().toString(),
                timestamp: new Date().toISOString(),
                source,
                message,
                priority: data.priority,
            };
            setLog([newLogEntry, ...log]);
        } catch (err) {
            console.error(err);
            alert("Error classifying interruption.");
        } finally {
            setLoading(false);
        }
    };

    const loadExample = (ex: { msg: string; source: string }) => {
        setMessage(ex.msg);
        setSource(ex.source);
        setResult(null);
    };

    return (
        <div className="p-6 max-w-4xl mx-auto space-y-6 animate-in">
            {/* Header */}
            <div className="pt-2">
                <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                    <Zap size={20} />
                    Focus Shield
                </h1>
                <p className="text-sm text-zinc-500 mt-0.5">
                    AI-powered interruption triage — stay in flow, handle what matters
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                {/* Form (left) */}
                <div className="lg:col-span-3 space-y-4">
                    {/* Examples */}
                    <div className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-4 space-y-3">
                        <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600">
                            Try an example
                        </p>
                        <div className="space-y-2">
                            {EXAMPLES.map((ex, i) => (
                                <button
                                    key={i}
                                    onClick={() => loadExample(ex)}
                                    className="w-full text-left border border-[#1a1a1a] hover:border-[#333] rounded-lg p-3 transition-all group"
                                >
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-[10px] font-mono uppercase text-zinc-700 bg-zinc-900 px-1.5 py-0.5 rounded-sm">
                                            {ex.source}
                                        </span>
                                    </div>
                                    <p className="text-xs text-zinc-400 group-hover:text-zinc-200 transition-colors line-clamp-1">
                                        "{ex.msg}"
                                    </p>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Classify Form */}
                    <form
                        onSubmit={handleSubmit}
                        className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-5 space-y-4"
                    >
                        <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600">
                            Classify Interruption
                        </p>

                        {/* Source */}
                        <div>
                            <label className="block text-xs font-mono text-zinc-500 mb-2">Source</label>
                            <div className="flex flex-wrap gap-1.5">
                                {SOURCES.map((s) => (
                                    <button
                                        key={s.value}
                                        type="button"
                                        onClick={() => setSource(s.value)}
                                        className={`text-[11px] font-mono px-2.5 py-1 rounded border transition-all ${source === s.value
                                            ? "bg-white text-black border-white"
                                            : "text-zinc-500 border-[#222] hover:border-[#444]"
                                            }`}
                                    >
                                        {s.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Message */}
                        <div>
                            <label className="block text-xs font-mono text-zinc-500 mb-2">
                                Interruption Message
                            </label>
                            <textarea
                                required
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                rows={4}
                                placeholder="Paste the message you received..."
                                className="w-full bg-black border border-[#222] focus:border-[#444] rounded px-3 py-2.5 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors resize-none"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading || !message.trim()}
                            className="w-full flex items-center justify-center gap-2 bg-white text-black text-sm font-semibold py-2.5 rounded hover:bg-zinc-200 disabled:opacity-50 transition-all"
                        >
                            {loading ? (
                                <Loader2 size={14} className="animate-spin" />
                            ) : (
                                <Zap size={14} />
                            )}
                            {loading ? "Analyzing..." : "Classify & Get Auto-Reply"}
                        </button>
                    </form>

                    {/* Result */}
                    {result && !loading && (
                        <div
                            className={`border rounded-xl p-5 space-y-4 animate-in ${result.priority === "critical"
                                ? "border-red-900/40 bg-red-950/10"
                                : result.priority === "important"
                                    ? "border-yellow-900/40 bg-yellow-950/10"
                                    : "border-emerald-900/40 bg-emerald-950/10"
                                }`}
                        >
                            <div className="flex items-center gap-3">
                                <PriorityBadge priority={result.priority} />
                                <p className="text-xs text-zinc-400">{result.reason}</p>
                            </div>

                            {result.auto_reply && (
                                <div>
                                    <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-2 flex items-center gap-1.5">
                                        <MessageSquare size={10} />
                                        Auto-Reply (copy & send)
                                    </p>
                                    <div className="border border-[#1a1a1a] bg-black/40 rounded-lg p-3">
                                        <p className="text-xs text-zinc-300 leading-relaxed font-mono">
                                            {result.auto_reply}
                                        </p>
                                    </div>
                                </div>
                            )}

                            <div>
                                <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-1.5">
                                    Action Required
                                </p>
                                <p className="text-xs text-zinc-300 font-mono">{result.action_required}</p>
                            </div>

                            {result.defer_duration_minutes > 0 && (
                                <div className="flex items-center gap-2 text-xs text-zinc-600 font-mono">
                                    <Clock size={11} />
                                    Suggested defer: {result.defer_duration_minutes >= 60
                                        ? `${Math.round(result.defer_duration_minutes / 60)}h`
                                        : `${result.defer_duration_minutes}m`}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Log (right) */}
                <div className="lg:col-span-2">
                    <div className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-4">
                        <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-4">
                            Today&apos;s Interruption Log
                        </p>
                        <div className="space-y-2.5">
                            {log.map((item) => (
                                <div
                                    key={item.id}
                                    className="border border-[#111] rounded-lg p-3 space-y-1.5"
                                >
                                    <div className="flex items-center justify-between">
                                        <span className="text-[10px] font-mono text-zinc-600">
                                            {item.timestamp}
                                        </span>
                                        <PriorityBadge priority={item.priority} size="xs" />
                                    </div>
                                    <p className="text-xs text-zinc-400 line-clamp-1 font-mono">
                                        [{item.source}] {item.message}
                                    </p>
                                </div>
                            ))}
                        </div>
                        <div className="mt-4 pt-3 border-t border-[#111] text-center">
                            <p className="text-xs text-zinc-700 font-mono">
                                3 interruptions deferred today · ~2.5h focus saved
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
