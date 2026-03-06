"use client";
import { useState } from "react";
import { GitBranch, Loader2, Download } from "lucide-react";
import DiagramViewer from "@/components/DiagramViewer";
import { API_URL } from "@/lib/config";

const DIAGRAM_TYPES = [
    { value: "sequence", label: "Sequence" },
    { value: "flowchart", label: "Flowchart" },
    { value: "class", label: "Class Diagram" },
];

const EXAMPLE_QUERIES = [
    "Show payment flow from checkout to order creation",
    "Auth token validation sequence",
    "API request lifecycle",
    "Service dependency graph",
];

export default function DiagramPage() {
    const [query, setQuery] = useState("");
    const [type, setType] = useState("sequence");
    const [projectPath, setProjectPath] = useState("/projects/myapp/backend");
    const [loading, setLoading] = useState(false);
    const [diagram, setDiagram] = useState<string | null>(null);

    const handleGenerate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;
        setLoading(true);
        setDiagram(null);

        try {
            const res = await fetch(`${API_URL}/diagram`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query,
                    project_path: projectPath,
                    diagram_type: type
                }),
            });

            if (!res.ok) throw new Error("Failed to generate diagram");

            const data = await res.json();
            setDiagram(data.mermaid);
        } catch (err) {
            console.error(err);
            alert("Error generating diagram.");
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = () => {
        if (!diagram) return;
        const blob = new Blob([diagram], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "diagram.mmd";
        a.click();
    };

    return (
        <div className="p-6 max-w-5xl mx-auto space-y-6 animate-in">
            {/* Header */}
            <div className="pt-2">
                <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                    <GitBranch size={20} />
                    Architecture Diagrams
                </h1>
                <p className="text-sm text-zinc-500 mt-0.5">
                    Generate Mermaid.js diagrams from natural language queries
                </p>
            </div>

            {/* Form */}
            <form
                onSubmit={handleGenerate}
                className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-5 space-y-4"
            >
                {/* Diagram Type */}
                <div>
                    <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-2">
                        Diagram Type
                    </p>
                    <div className="flex gap-2">
                        {DIAGRAM_TYPES.map((t) => (
                            <button
                                key={t.value}
                                type="button"
                                onClick={() => setType(t.value)}
                                className={`text-xs font-mono px-3 py-1.5 rounded border transition-all ${type === t.value
                                    ? "bg-white text-black border-white"
                                    : "text-zinc-500 border-[#222] hover:border-[#444] hover:text-zinc-300"
                                    }`}
                            >
                                {t.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Examples */}
                <div>
                    <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-2">
                        Examples
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                        {EXAMPLE_QUERIES.map((q) => (
                            <button
                                key={q}
                                type="button"
                                onClick={() => setQuery(q)}
                                className="text-[10px] font-mono text-zinc-500 hover:text-zinc-300 border border-[#1a1a1a] hover:border-[#333] px-2 py-0.5 rounded-sm transition-all"
                            >
                                {q}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Project Path */}
                <div>
                    <label className="block text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-2">
                        Project Path
                    </label>
                    <input
                        value={projectPath}
                        onChange={(e) => setProjectPath(e.target.value)}
                        placeholder="/projects/myapp"
                        className="w-full bg-black border border-[#222] focus:border-[#444] rounded px-3 py-2 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors"
                    />
                </div>

                {/* Query Input */}
                <div>
                    <label className="block text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-2">
                        Query
                    </label>
                    <div className="flex gap-2">
                        <input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Show payment flow from checkout to order creation"
                            className="flex-1 bg-black border border-[#222] focus:border-[#444] rounded px-3 py-2.5 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors"
                        />
                        <button
                            type="submit"
                            disabled={loading || !query.trim()}
                            className="flex items-center gap-1.5 bg-white text-black text-sm font-semibold px-5 py-2.5 rounded hover:bg-zinc-200 disabled:opacity-50 transition-all flex-shrink-0"
                        >
                            {loading ? (
                                <Loader2 size={14} className="animate-spin" />
                            ) : (
                                <GitBranch size={14} />
                            )}
                            Generate
                        </button>
                    </div>
                </div>
            </form>

            {/* Diagram result */}
            {(loading || diagram) && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600">
                            Generated Diagram
                        </p>
                        {diagram && !loading && (
                            <button
                                onClick={handleDownload}
                                className="flex items-center gap-1.5 text-xs font-mono text-zinc-500 hover:text-zinc-300 border border-[#1a1a1a] hover:border-[#333] px-2.5 py-1 rounded transition-all"
                            >
                                <Download size={11} />
                                Download .mmd
                            </button>
                        )}
                    </div>

                    <DiagramViewer diagram={diagram || ""} loading={loading} />

                    {/* Raw mermaid source */}
                    {diagram && !loading && (
                        <details className="group">
                            <summary className="text-[10px] font-mono text-zinc-700 cursor-pointer hover:text-zinc-500 transition-colors select-none">
                                View Mermaid source ▾
                            </summary>
                            <pre className="mt-2 p-4 border border-[#1a1a1a] bg-[#050505] rounded-lg text-xs font-mono text-zinc-500 overflow-auto">
                                {diagram}
                            </pre>
                        </details>
                    )}
                </div>
            )}
        </div>
    );
}
