"use client";
import { useState } from "react";
import { Bookmark, Plus, X, Loader2, CheckCircle, Tag } from "lucide-react";
import { API_URL } from "@/lib/config";

const EXAMPLE_TODOS = [
    "Fix token expiry validation bug on line 142",
    "Add unit tests for the auth middleware",
    "Update API docs for /refresh-token endpoint",
];

const EXAMPLE_COMMANDS = [
    "npm run test:unit",
    "git diff HEAD~1 --stat",
    "docker-compose up -d postgres",
];

type FormState = {
    name: string;
    project_path: string;
    active_file: string;
    open_files: string;
    todos: string;
    terminal_commands: string;
    tags: string;
};

const initialForm: FormState = {
    name: "",
    project_path: "",
    active_file: "",
    open_files: "",
    todos: "",
    terminal_commands: "",
    tags: "",
};

type ResultState = {
    ai_summary: string;
    next_steps: string[];
    saved: boolean;
} | null;

export default function CheckpointPage() {
    const [form, setForm] = useState<FormState>(initialForm);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<ResultState>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setResult(null);

        try {
            const payload = {
                name: form.name,
                project_path: form.project_path,
                active_file: form.active_file,
                open_files: form.open_files.split("\n").filter(Boolean).map(f => ({ path: f.trim(), status: "modified" })),
                recent_edits: [],
                todos: form.todos.split("\n").filter(Boolean),
                tags: form.tags.split(",").map(t => t.trim()).filter(Boolean),
            };

            const res = await fetch(`${API_URL}/snapshots`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!res.ok) throw new Error("Failed to save checkpoint");

            const data = await res.json();

            setResult({
                ai_summary: data.ai_summary,
                next_steps: data.next_steps,
                saved: true,
            });
        } catch (err) {
            console.error(err);
            alert("Error saving checkpoint. Is the backend running?");
        } finally {
            setLoading(false);
        }
    };

    const addExample = () => {
        setForm({
            name: "JWT Auth Refactor",
            project_path: "/projects/myapp/backend",
            active_file: "backend/auth/auth.service.ts",
            open_files: "auth.service.ts\njwt.util.ts\nPaymentService.ts\nOrderService.ts",
            todos: EXAMPLE_TODOS.join("\n"),
            terminal_commands: EXAMPLE_COMMANDS.join("\n"),
            tags: "auth, backend, refactor",
        });
    };

    return (
        <div className="p-6 max-w-3xl mx-auto space-y-6 animate-in">
            {/* Header */}
            <div className="flex items-center justify-between pt-2">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                        <Bookmark size={20} />
                        Checkpoint Work
                    </h1>
                    <p className="text-sm text-zinc-500 mt-0.5">
                        Save your current work state with AI-generated context summary
                    </p>
                </div>
                <button
                    type="button"
                    onClick={addExample}
                    className="text-xs font-mono text-zinc-500 hover:text-zinc-300 border border-[#1a1a1a] hover:border-[#333] px-3 py-1.5 rounded transition-all"
                >
                    Load Example
                </button>
            </div>

            {/* Form */}
            <form
                onSubmit={handleSubmit}
                className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-6 space-y-5"
            >
                {/* Row 1 */}
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1.5">
                            Checkpoint Name *
                        </label>
                        <input
                            required
                            value={form.name}
                            onChange={(e) => setForm({ ...form, name: e.target.value })}
                            placeholder="e.g. JWT Auth Refactor"
                            className="w-full bg-black border border-[#222] focus:border-[#444] rounded px-3 py-2 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1.5">
                            Project Path
                        </label>
                        <input
                            value={form.project_path}
                            onChange={(e) => setForm({ ...form, project_path: e.target.value })}
                            placeholder="/projects/myapp"
                            className="w-full bg-black border border-[#222] focus:border-[#444] rounded px-3 py-2 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors"
                        />
                    </div>
                </div>

                {/* Active File */}
                <div>
                    <label className="block text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1.5">
                        Active File
                    </label>
                    <input
                        value={form.active_file}
                        onChange={(e) => setForm({ ...form, active_file: e.target.value })}
                        placeholder="backend/auth/auth.service.ts"
                        className="w-full bg-black border border-[#222] focus:border-[#444] rounded px-3 py-2 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors"
                    />
                </div>

                {/* Open Files + TODOs */}
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1.5">
                            Open Files (one per line)
                        </label>
                        <textarea
                            value={form.open_files}
                            onChange={(e) => setForm({ ...form, open_files: e.target.value })}
                            rows={4}
                            placeholder={"auth.service.ts\njwt.util.ts\nPaymentService.ts"}
                            className="w-full bg-black border border-[#222] focus:border-[#444] rounded px-3 py-2 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors resize-none"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1.5">
                            TODOs (one per line)
                        </label>
                        <textarea
                            value={form.todos}
                            onChange={(e) => setForm({ ...form, todos: e.target.value })}
                            rows={4}
                            placeholder={"Fix token expiry bug\nAdd unit tests\nUpdate docs"}
                            className="w-full bg-black border border-[#222] focus:border-[#444] rounded px-3 py-2 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors resize-none"
                        />
                    </div>
                </div>

                {/* Terminal Commands */}
                <div>
                    <label className="block text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1.5">
                        Recent Terminal Commands
                    </label>
                    <textarea
                        value={form.terminal_commands}
                        onChange={(e) =>
                            setForm({ ...form, terminal_commands: e.target.value })
                        }
                        rows={3}
                        placeholder={"npm run test\ngit diff HEAD~1\ndocker-compose up"}
                        className="w-full bg-black border border-[#222] focus:border-[#444] rounded px-3 py-2 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors resize-none"
                    />
                </div>

                {/* Tags */}
                <div>
                    <label className="block text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1.5">
                        Tags (comma-separated)
                    </label>
                    <div className="relative">
                        <Tag
                            size={13}
                            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600"
                        />
                        <input
                            value={form.tags}
                            onChange={(e) => setForm({ ...form, tags: e.target.value })}
                            placeholder="auth, backend, refactor"
                            className="w-full bg-black border border-[#222] focus:border-[#444] rounded pl-8 pr-3 py-2 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors"
                        />
                    </div>
                </div>

                {/* Submit */}
                <div className="flex items-center justify-between pt-2 border-t border-[#111]">
                    <button
                        type="button"
                        onClick={() => { setForm(initialForm); setResult(null); }}
                        className="text-xs font-mono text-zinc-600 hover:text-zinc-400 transition-colors"
                    >
                        Clear form
                    </button>
                    <button
                        type="submit"
                        disabled={loading}
                        className="flex items-center gap-2 bg-white text-black text-sm font-semibold px-5 py-2 rounded hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        {loading ? (
                            <>
                                <Loader2 size={14} className="animate-spin" />
                                Generating Context...
                            </>
                        ) : (
                            <>
                                <Bookmark size={14} />
                                Save Checkpoint
                            </>
                        )}
                    </button>
                </div>
            </form>

            {/* Result */}
            {result && (
                <div className="border border-emerald-900/40 bg-emerald-950/10 rounded-xl p-6 space-y-4 animate-in">
                    <div className="flex items-center gap-2">
                        <CheckCircle size={16} className="text-emerald-400" />
                        <span className="text-sm font-semibold text-emerald-400">
                            Checkpoint Saved — AI Context Generated
                        </span>
                    </div>

                    <div>
                        <p className="text-[10px] font-mono uppercase tracking-widest text-zinc-600 mb-2">
                            AI Thought Log
                        </p>
                        <p className="text-sm text-zinc-300 leading-relaxed border-l-2 border-zinc-700 pl-3">
                            {result.ai_summary}
                        </p>
                    </div>

                    <div>
                        <p className="text-[10px] font-mono uppercase tracking-widest text-zinc-600 mb-2">
                            Next Steps
                        </p>
                        <ul className="space-y-1.5">
                            {result.next_steps.map((step, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm text-zinc-400 font-mono">
                                    <span className="text-zinc-700 mt-0.5 flex-shrink-0">
                                        {i + 1}.
                                    </span>
                                    {step}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}
        </div>
    );
}
