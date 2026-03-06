import { clsx } from "clsx";

type Priority = "critical" | "important" | "deferrable";

const labels: Record<Priority, string> = {
    critical: "CRITICAL",
    important: "IMPORTANT",
    deferrable: "DEFERRABLE",
};

const styles: Record<Priority, string> = {
    critical: "bg-red-950/60 text-red-400 border border-red-800/50",
    important: "bg-yellow-950/60 text-yellow-400 border border-yellow-800/50",
    deferrable: "bg-emerald-950/60 text-emerald-400 border border-emerald-800/50",
};

export default function PriorityBadge({
    priority,
    size = "sm",
}: {
    priority: Priority | string;
    size?: "xs" | "sm";
}) {
    const p = (priority as Priority) ?? "deferrable";
    return (
        <span
            className={clsx(
                "inline-flex items-center font-mono font-semibold rounded-sm tracking-wider",
                styles[p] ?? styles.deferrable,
                size === "xs" ? "px-1.5 py-0.5 text-[9px]" : "px-2 py-0.5 text-[10px]"
            )}
        >
            {labels[p] ?? priority.toUpperCase()}
        </span>
    );
}
