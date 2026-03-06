"use client";
import { useEffect, useRef, useState } from "react";

interface DiagramViewerProps {
    diagram: string;
    loading?: boolean;
}

export default function DiagramViewer({ diagram, loading }: DiagramViewerProps) {
    const ref = useRef<HTMLDivElement>(null);
    const [error, setError] = useState<string | null>(null);
    const [rendered, setRendered] = useState(false);

    useEffect(() => {
        if (!diagram || loading) return;

        const renderDiagram = async () => {
            try {
                const mermaid = (await import("mermaid")).default;
                mermaid.initialize({
                    startOnLoad: false,
                    theme: "dark",
                    securityLevel: "loose",

                    flowchart: {
                        nodeSpacing: 20,
                        rankSpacing: 25,
                        padding: 10,
                        curve: "basis"
                    },

                    themeVariables: {
                        primaryColor: "#1a1a1a",
                        primaryTextColor: "#ffffff",
                        primaryBorderColor: "#333333",
                        lineColor: "#555555",
                        secondaryColor: "#111111",
                        tertiaryColor: "#0a0a0a",
                        background: "#000000",
                        mainBkg: "#0a0a0a",
                        nodeBorder: "#333",
                        clusterBkg: "#111111",
                        titleColor: "#ffffff",
                        edgeLabelBackground: "#000000",
                        actorBkg: "#111111",
                        actorBorder: "#333333",
                        actorTextColor: "#ffffff",
                        signalColor: "#999999",
                        signalTextColor: "#ffffff",
                    },

                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 13,
                });

                const id = `mermaid-${Date.now()}`;
                const { svg } = await mermaid.render(id, diagram);
                if (ref.current) {
                    ref.current.innerHTML = svg;
                    setRendered(true);
                    setError(null);
                }
            } catch (e) {
                setError("Failed to render diagram. The syntax may be invalid.");
                console.error(e);
            }
        };

        renderDiagram();
    }, [diagram, loading]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-48 border border-[#1a1a1a] rounded-lg bg-[#050505]">
                <div className="flex items-center gap-3 text-zinc-500">
                    <div className="w-4 h-4 border border-zinc-600 border-t-white rounded-full animate-spin" />
                    <span className="text-sm font-mono">Generating diagram...</span>
                </div>
            </div>
        );
    }

    if (!diagram) return null;

    if (error) {
        return (
            <div className="border border-red-900/40 rounded-lg bg-red-950/10 p-4">
                <p className="text-red-400 text-sm font-mono">{error}</p>
                <pre className="mt-3 text-xs text-zinc-500 font-mono overflow-auto">{diagram}</pre>
            </div>
        );
    }

    return (
        <div className="border border-[#1a1a1a] rounded-lg bg-[#050505] p-4 overflow-auto animate-in">
            <div ref={ref} className="mermaid flex items-center justify-center min-h-32" />
        </div>
    );
}
