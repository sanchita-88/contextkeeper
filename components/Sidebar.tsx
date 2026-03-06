"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
    LayoutDashboard,
    Bookmark,
    Search,
    GitBranch,
    Zap,
    ChevronRight,
    Terminal,
} from "lucide-react";
import clsx from "clsx";

const nav = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Checkpoint", href: "/dashboard/checkpoint", icon: Bookmark },
    { label: "Codebase Q&A", href: "/dashboard/codebase", icon: Search },
    { label: "Diagrams", href: "/dashboard/diagram", icon: GitBranch },
    { label: "Focus Shield", href: "/dashboard/interruptions", icon: Zap },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="fixed left-0 top-0 h-full w-56 bg-gradient-to-b from-[#050505] to-black border-r border-white/5 flex flex-col z-40 shadow-[4px_0_24px_rgba(0,0,0,0.5)]">
            {/* Logo */}
            <div className="px-4 py-5 border-b border-white/5 bg-white/[0.02]">
                <Link href="/" className="flex items-center gap-3 group">
                    <div className="w-8 h-8 rounded bg-gradient-to-tr from-purple-600 to-blue-500 flex items-center justify-center shadow-lg shadow-purple-500/20 group-hover:shadow-purple-500/40 transition-all border border-white/10">
                        <Terminal size={14} className="text-white" strokeWidth={2.5} />
                    </div>
                    <span className="font-semibold tracking-tight text-white group-hover:text-purple-200 transition-colors">
                        ContextKeeper
                    </span>
                </Link>
            </div>

            {/* Nav */}
            <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
                <p className="text-[10px] uppercase tracking-widest text-zinc-600 px-3 pt-3 pb-2 font-mono drop-shadow-sm">
                    Workspace
                </p>
                {nav.map(({ label, href, icon: Icon }) => {
                    const active =
                        href === "/dashboard"
                            ? pathname === "/dashboard"
                            : pathname.startsWith(href);
                    return (
                        <Link
                            key={href}
                            href={href}
                            className="block relative"
                        >
                            <div
                                className={clsx(
                                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all z-10 relative",
                                    active
                                        ? "text-white"
                                        : "text-zinc-400 hover:text-white hover:bg-white/5"
                                )}
                            >
                                <Icon
                                    size={16}
                                    strokeWidth={active ? 2.5 : 2}
                                    className={active ? "text-purple-400" : ""}
                                />
                                <span>{label}</span>
                                {active && (
                                    <ChevronRight size={14} className="ml-auto text-purple-400 opacity-60" />
                                )}
                            </div>
                            {active && (
                                <motion.div
                                    layoutId="active-nav"
                                    className="absolute inset-0 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-white/5 rounded-lg z-0 pointer-events-none shadow-[inset_0_0_15px_rgba(168,85,247,0.1)]"
                                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                />
                            )}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="p-4 border-t border-white/5 bg-white/[0.01]">
                <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer border border-transparent hover:border-white/5">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-zinc-800 to-zinc-900 border border-white/10 flex items-center justify-center text-[10px] font-mono text-zinc-300 shadow-inner">
                        D
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-zinc-200 truncate">Dev User</p>
                        <p className="text-[10px] text-purple-400/80 truncate font-mono tracking-wide">Pro Tier</p>
                    </div>
                </div>
            </div>
        </aside>
    );
}
