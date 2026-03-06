"use client";
import { useState, useEffect } from "react";
import { Search, Database, Loader2, FileCode, ChevronRight } from "lucide-react";
import DiagramViewer from "@/components/DiagramViewer";
import { API_URL } from "@/lib/config";

const EXAMPLE_QUESTIONS = [
    "How does authentication work?",
    "What happens when a payment fails?",
    "How is the order service connected to email?",
    "Explain the JWT token flow",
];

type QAResult = {
    answer: string;
    relevant_files: string[];
    code_snippets: { file_path: string; start_line: number; end_line: number; content: string }[];
    mermaid_diagram: string | null;
};

type RepoState = {
    name: string;
    path: string;
    files: number;
    chunks: number;
};

export default function CodebasePage() {
    const [repos, setRepos] = useState<RepoState[]>([]);
    const [selectedRepo, setSelectedRepo] = useState<RepoState | null>(null);
    const [newRepoPath, setNewRepoPath] = useState("");
    const [question, setQuestion] = useState("");
    const [loading, setLoading] = useState(false);
    const [indexing, setIndexing] = useState(false);
    const [indexProgress, setIndexProgress] = useState(0);
    const [result, setResult] = useState<QAResult | null>(null);

    const handleAsk = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!question.trim() || !selectedRepo) return;
        setLoading(true);
        setResult(null);

        try {
            const res = await fetch(`${API_URL}/query`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question,
                    project_path: selectedRepo.path,
                }),
            });

            if (!res.ok) throw new Error("Query failed");

            const data = await res.json();
            setResult(data);
        } catch (err) {
            console.error(err);
            alert("Error querying codebase. Is it indexed?");
        } finally {
            setLoading(false);
        }
    };

    const handleIndex = async () => {
        if (!newRepoPath.trim()) return;
        setIndexing(true);
        setIndexProgress(0);

        try {
            const res = await fetch(`${API_URL}/index`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ project_path: newRepoPath }),
            });

            if (!res.ok) throw new Error("Indexing failed to start");

            // Poll status immediately
            const interval = setInterval(async () => {
                const statusRes = await fetch(`${API_URL}/index/status?project_path=${encodeURIComponent(newRepoPath)}`);
                if (statusRes.ok) {
                    const status = await statusRes.json();
                    setIndexProgress(Math.floor(status.progress * 100));

                    if (status.indexed) {
                        clearInterval(interval);
                        setIndexing(false);
                        const newRepo = {
                            name: newRepoPath.split("/").pop() || newRepoPath,
                            path: newRepoPath,
                            files: status.file_count,
                            chunks: status.chunk_count,
                        };
                        setRepos([newRepo, ...repos]);
                        setSelectedRepo(newRepo);
                        setNewRepoPath("");
                    }
                }
            }, 1000);
        } catch (err) {
            console.error(err);
            alert("Error starting indexing process");
            setIndexing(false);
        }
    };

    return (
        <div className="p-6 max-w-5xl mx-auto space-y-6 animate-in">
            {/* Header */}
            <div className="pt-2">
                <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                    <Search size={20} />
                    Codebase Intelligence
                </h1>
                <p className="text-sm text-zinc-500 mt-0.5">
                    Ask anything about your indexed repositories
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Left: Repo List */}
                <div className="space-y-3">
                    <div>
                        <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-2">
                            Indexed Repos
                        </p>
                        <div className="space-y-1.5">
                            {repos.length === 0 ? (
                                <p className="text-xs text-zinc-500 font-mono italic p-2">No repos indexed. Ingest one below.</p>
                            ) : (
                                repos.map((repo) => (
                                    <button
                                        key={repo.path}
                                        onClick={() => setSelectedRepo(repo)}
                                        className={`w-full text-left border rounded-lg p-3 transition-all ${selectedRepo && selectedRepo.path === repo.path
                                            ? "border-[#444] bg-[#0f0f0f]"
                                            : "border-[#1a1a1a] bg-[#050505] hover:border-[#333]"
                                            }`}
                                    >
                                        <div className="flex items-center gap-2 mb-1">
                                            <Database size={11} className="text-zinc-500" />
                                            <span className="text-xs font-mono font-medium text-white truncate">
                                                {repo.name}
                                            </span>
                                        </div>
                                        <div className="text-[10px] text-zinc-600 font-mono">
                                            {repo.files} files · {repo.chunks} chunks
                                        </div>
                                    </button>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Index New Repo */}
                    <div className="border border-[#1a1a1a] rounded-lg p-3 space-y-2">
                        <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600">
                            Index New Repo
                        </p>
                        <input
                            value={newRepoPath}
                            onChange={e => setNewRepoPath(e.target.value)}
                            placeholder="D:/my/local/project"
                            className="w-full bg-black border border-[#222] focus:border-[#444] rounded px-2.5 py-1.5 text-xs text-white font-mono placeholder-zinc-700 outline-none transition-colors"
                        />
                        <button
                            onClick={handleIndex}
                            disabled={indexing}
                            className="w-full bg-white text-black text-xs font-semibold py-1.5 rounded hover:bg-zinc-200 disabled:opacity-50 transition-all flex items-center justify-center gap-1.5"
                        >
                            {indexing ? (
                                <Loader2 size={11} className="animate-spin" />
                            ) : (
                                <Database size={11} />
                            )}
                            {indexing ? "Indexing..." : "Ingest & Index"}
                        </button>
                        {indexing && (
                            <div className="w-full bg-zinc-900 rounded-full h-1">
                                <div
                                    className="bg-white h-1 rounded-full transition-all duration-200"
                                    style={{ width: `${indexProgress}%` }}
                                />
                            </div>
                        )}
                        {!indexing && indexProgress === 100 && (
                            <p className="text-[10px] text-emerald-400 font-mono">
                                ✓ Indexed successfully
                            </p>
                        )}
                    </div>
                </div>

                {/* Right: Q&A */}
                <div className="lg:col-span-2 space-y-4">
                    {/* Ask form */}
                    <form onSubmit={handleAsk} className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-4">
                        <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-3">
                            Ask a question about{" "}
                            <span className="text-zinc-400">{selectedRepo ? selectedRepo.name : "your codebase"}</span>
                        </p>

                        {/* Example questions */}
                        <div className="flex flex-wrap gap-1.5 mb-3">
                            {EXAMPLE_QUESTIONS.map((q) => (
                                <button
                                    key={q}
                                    type="button"
                                    onClick={() => setQuestion(q)}
                                    className="text-[10px] font-mono text-zinc-500 hover:text-zinc-300 border border-[#1a1a1a] hover:border-[#333] px-2 py-0.5 rounded-sm transition-all"
                                >
                                    {q}
                                </button>
                            ))}
                        </div>

                        <div className="flex gap-2">
                            <input
                                value={question}
                                onChange={(e) => setQuestion(e.target.value)}
                                placeholder="How does authentication work?"
                                className="flex-1 bg-black border border-[#222] focus:border-[#444] rounded px-3 py-2 text-sm text-white font-mono placeholder-zinc-700 outline-none transition-colors"
                            />
                            <button
                                type="submit"
                                disabled={loading || !question.trim()}
                                className="flex items-center gap-1.5 bg-white text-black text-xs font-semibold px-4 py-2 rounded hover:bg-zinc-200 disabled:opacity-50 transition-all flex-shrink-0"
                            >
                                {loading ? (
                                    <Loader2 size={13} className="animate-spin" />
                                ) : (
                                    <Search size={13} />
                                )}
                                Ask AI
                            </button>
                        </div>
                    </form>

                    {/* Result */}
                    {loading && (
                        <div className="border border-[#1a1a1a] rounded-xl p-6 flex items-center gap-3 text-zinc-500">
                            <Loader2 size={16} className="animate-spin" />
                            <span className="text-sm font-mono">
                                Searching codebase and generating answer...
                            </span>
                        </div>
                    )}

                    {result && !loading && (
                        <div className="space-y-4 animate-in">
                            {/* Answer */}
                            <div className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-5">
                                <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-3">
                                    AI Answer
                                </p>
                                <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">
                                    {result.answer}
                                </div>
                            </div>

                            {/* Code Snippets */}
                            {result.code_snippets.map((snippet, i) => (
                                <div
                                    key={i}
                                    className="border border-[#1a1a1a] bg-[#050505] rounded-xl overflow-hidden"
                                >
                                    <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[#111] bg-[#0a0a0a]">
                                        <FileCode size={12} className="text-zinc-600" />
                                        <span className="text-xs font-mono text-zinc-400">
                                            {snippet.file_path}
                                        </span>
                                        <span className="ml-auto text-[10px] font-mono text-zinc-700">
                                            L{snippet.start_line}–{snippet.end_line}
                                        </span>
                                    </div>
                                    <pre className="p-4 text-xs font-mono text-zinc-400 overflow-auto leading-relaxed">
                                        {snippet.content}
                                    </pre>
                                </div>
                            ))}

                            {/* Relevant Files */}
                            <div className="border border-[#1a1a1a] bg-[#050505] rounded-xl p-4">
                                <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-2.5">
                                    Relevant Files
                                </p>
                                <div className="space-y-1.5">
                                    {result.relevant_files.map((f) => (
                                        <div key={f} className="flex items-center gap-2 text-xs font-mono text-zinc-400">
                                            <ChevronRight size={11} className="text-zinc-700" />
                                            {f}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Mermaid Diagram */}
                            {result.mermaid_diagram && (
                                <div>
                                    <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600 mb-2.5">
                                        Architecture Diagram
                                    </p>
                                    <DiagramViewer diagram={result.mermaid_diagram} />
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
