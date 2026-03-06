import Link from "next/link";
import { Clock, Tag, ChevronRight, FileCode, Zap } from "lucide-react";

interface Snapshot {
    id: string;
    name: string;
    timestamp: string;
    project_path: string;
    ai_summary: string;
    next_steps: string[];
    tags: string[];
    active_file: string;
    time_spent_minutes: number;
    open_files_count?: number;
}

function timeAgo(timestamp: string): string {
    const now = Date.now();
    const then = new Date(timestamp).getTime();
    const diff = now - then;
    const mins = Math.floor(diff / 60000);
    const hrs = Math.floor(mins / 60);
    const days = Math.floor(hrs / 24);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    if (hrs < 24) return `${hrs}h ago`;
    return `${days}d ago`;
}

export default function SnapshotCard({ snapshot }: { snapshot: Snapshot }) {
    const fileName = snapshot.active_file?.split("/").pop() || "Unknown file";

    return (
        <div className="group border border-[#1a1a1a] hover:border-[#333] rounded-lg bg-[#050505] hover:bg-[#0a0a0a] transition-all duration-200 p-4 animate-in">
            {/* Header */}
            <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0">
                    <h3 className="font-semibold text-sm text-white truncate group-hover:text-white transition-colors">
                        {snapshot.name}
                    </h3>
                    <div className="flex items-center gap-3 mt-0.5">
                        <span className="flex items-center gap-1 text-xs text-zinc-600 font-mono">
                            <Clock size={10} />
                            {timeAgo(snapshot.timestamp)}
                        </span>
                        <span className="flex items-center gap-1 text-xs text-zinc-600 font-mono">
                            <FileCode size={10} />
                            {fileName}
                        </span>
                        {snapshot.time_spent_minutes > 0 && (
                            <span className="flex items-center gap-1 text-xs text-zinc-600 font-mono">
                                <Zap size={10} />
                                {snapshot.time_spent_minutes}m
                            </span>
                        )}
                    </div>
                </div>
                <Link
                    href={`/dashboard/resume/${snapshot.id}`}
                    className="flex-shrink-0 flex items-center gap-1 text-[11px] font-medium font-mono bg-white text-black hover:bg-zinc-200 px-2.5 py-1.5 rounded transition-all"
                >
                    Resume
                    <ChevronRight size={10} strokeWidth={3} />
                </Link>
            </div>

            {/* AI Summary */}
            {snapshot.ai_summary && (
                <p className="text-xs text-zinc-400 leading-relaxed line-clamp-2 mb-3 border-l-2 border-zinc-800 pl-2.5">
                    {snapshot.ai_summary}
                </p>
            )}

            {/* Next Steps Preview */}
            {snapshot.next_steps && snapshot.next_steps.length > 0 && (
                <div className="mb-3">
                    <div className="flex items-center gap-1.5 mb-1.5">
                        <span className="text-[9px] uppercase tracking-widest text-zinc-600 font-mono">
                            Next Steps
                        </span>
                    </div>
                    <ul className="space-y-0.5">
                        {snapshot.next_steps.slice(0, 2).map((step, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-[11px] text-zinc-500 font-mono">
                                <span className="text-zinc-700 mt-px">→</span>
                                <span className="line-clamp-1">{step}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Tags */}
            {snapshot.tags && snapshot.tags.length > 0 && (
                <div className="flex items-center gap-1.5 flex-wrap">
                    <Tag size={10} className="text-zinc-700" />
                    {snapshot.tags.map((tag) => (
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
    );
}
