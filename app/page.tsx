"use client";

import Link from "next/link";
import { motion, Variants } from "framer-motion";
import {
  Terminal,
  Bookmark,
  Search,
  GitBranch,
  Zap,
  ArrowRight,
  Code2,
  Database,
  Brain,
  ChevronRight,
  CheckCircle,
} from "lucide-react";

import dynamic from "next/dynamic";
const ThreejsBackground = dynamic(
  () => import("@/components/ThreejsBackground"),
  { ssr: false }
);

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6 } },
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const features = [
  {
    icon: Bookmark,
    title: "Context Snapshots",
    desc: "Capture your exact work state — open files, cursor positions, TODOs, and terminal history. Instantly resume later.",
  },
  {
    icon: Search,
    title: "Codebase Q&A",
    desc: "Ask anything about your repo in plain English. AI retrieves relevant code and explains architecture with diagrams.",
  },
  {
    icon: GitBranch,
    title: "Smart Diagrams",
    desc: "Auto-generate Mermaid.js sequence, flowchart, and class diagrams from your codebase relationships.",
  },
  {
    icon: Zap,
    title: "Focus Shield",
    desc: "AI classifies interruptions by urgency and generates professional defer replies so you stay in flow.",
  },
];

const stats = [
  { value: "$450B", label: "Lost to context switching annually" },
  { value: "23 min", label: "Average re-focus time after interruption" },
  { value: "4.8×", label: "Productivity boost with preservation" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white relative flex flex-col items-center selection:bg-purple-500/30">

      {/* 3D Background */}
      <ThreejsBackground />

      {/* Navbar */}
      <motion.nav
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="fixed top-0 inset-x-0 z-50 border-b border-white/5 bg-black/40 backdrop-blur-xl"
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 md:gap-4 group">
            <div className="relative w-9 h-9 flex items-center justify-center">
              <motion.div
                className="absolute inset-0 rounded-lg bg-gradient-to-tr from-purple-600 to-blue-600 opacity-80"
                animate={{ rotate: 360 }}
                transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
              />
              <motion.div
                className="absolute inset-[2px] rounded-md bg-black"
              />
              <div className="relative z-10 flex items-center justify-center w-full h-full">
                <Terminal size={16} className="text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" strokeWidth={2} />
              </div>
            </div>
            <span className="font-semibold text-[15px] tracking-tight hidden sm:block">ContextKeeper</span>
          </Link>

          <div className="hidden md:flex items-center gap-8 text-sm text-zinc-400 font-medium">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how" className="hover:text-white transition-colors">Engine</a>
            <a href="#stack" className="hover:text-white transition-colors">Stack</a>
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="text-xs text-zinc-300 hover:text-white transition-colors hidden sm:block font-medium"
            >
              Sign In
            </Link>
            <Link
              href="/dashboard"
              className="relative text-xs font-semibold bg-white text-black px-4 py-2 rounded-full overflow-hidden group transition-transform hover:scale-105"
            >
              <span className="relative z-10 flex items-center gap-1.5">
                Launch App <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-purple-200 to-white opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>
          </div>
        </div>
      </motion.nav>

      {/* Hero */}
      <section className="relative pt-32 md:pt-48 pb-20 px-6 w-full max-w-7xl mx-auto text-center z-10">

        {/* Glow behind text */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-purple-600/20 blur-[120px] rounded-full pointer-events-none" />

        <motion.div
          initial="hidden"
          animate="visible"
          variants={staggerContainer}
          className="relative"
        >
          <motion.div variants={fadeUp} className="flex justify-center mb-8">
            <div className="inline-flex items-center gap-2 border border-purple-500/30 bg-purple-500/10 text-purple-200 text-[11px] font-mono px-4 py-1.5 rounded-full shadow-[0_0_15px_rgba(168,85,247,0.15)] ring-1 ring-purple-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
              AI for Bharat Hackathon 2026
            </div>
          </motion.div>

          <motion.h1 variants={fadeUp} className="text-5xl md:text-8xl font-bold tracking-tighter leading-[1.05] mb-8">
            Your Memory Layer
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-zinc-500 via-zinc-400 to-zinc-600">
              for Code.
            </span>
          </motion.h1>

          <motion.p variants={fadeUp} className="text-zinc-400 text-lg md:text-xl max-w-2xl mx-auto mb-12 leading-relaxed font-light">
            Stop losing hours to context switching. ContextKeeper saves your exact
            work state, answers questions about your codebase, and gets you back
            to flow in <span className="text-white font-medium">under 60 seconds</span>.
          </motion.p>

          <motion.div variants={fadeUp} className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/dashboard"
              className="group relative flex items-center justify-center gap-2 bg-white text-black font-semibold px-8 py-3.5 rounded-full hover:scale-105 transition-all text-sm w-full sm:w-auto"
            >
              Start preserving context
              <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
            </Link>
          </motion.div>
        </motion.div>

        {/* Terminal Glass Preview */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.8, ease: "easeOut" }}
          className="mt-20 border border-white/10 bg-black/40 backdrop-blur-2xl rounded-2xl overflow-hidden text-left max-w-4xl mx-auto shadow-[0_0_50px_rgba(0,0,0,0.8)] ring-1 ring-white/5 relative"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-transparent to-transparent pointer-events-none" />
          <div className="flex items-center gap-2 px-5 py-4 border-b border-white/10 bg-white/[0.02]">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-zinc-800" />
              <div className="w-3 h-3 rounded-full bg-zinc-800" />
              <div className="w-3 h-3 rounded-full bg-zinc-800" />
            </div>
            <span className="ml-3 text-[11px] text-zinc-500 font-mono tracking-widest uppercase">ContextKeeper Engine v1.0</span>
          </div>
          <div className="p-6 md:p-8 font-mono text-sm space-y-3">
            <div className="flex text-zinc-300">
              <span className="text-purple-400 mr-2">~</span>
              <span className="text-blue-400 mr-2">❯</span>
              <span className="text-white">contextkeeper checkpoint --name "auth-refactor"</span>
            </div>
            <div className="text-zinc-500 pl-5 space-y-1.5 text-xs opacity-80">
              <p className="animate-[pulse_2s_ease-in-out_infinite]">▸ Capturing 7 open files...</p>
              <p className="animate-[pulse_2s_ease-in-out_infinite_0.5s]">▸ Indexing 23 recent edits into Qdrant...</p>
              <p className="animate-[pulse_2s_ease-in-out_infinite_1s]">▸ Passing diffs to Groq Llama-3...</p>
            </div>
            <div className="border-l-2 border-emerald-500/50 pl-4 mt-6 text-zinc-300 text-sm leading-relaxed bg-emerald-500/5 p-4 rounded-r-lg">
              <p className="text-emerald-400 font-bold mb-2 flex items-center gap-2">
                <CheckCircle size={14} /> Context Successfully Embedded
              </p>
              <p className="font-sans font-light">
                <strong className="font-semibold text-white">Summary:</strong> You were refactoring the JWT authentication service in <code className="bg-black/50 px-1.5 py-0.5 rounded text-xs text-purple-300">auth.service.ts</code>, specifically fixing the token expiry bug on line 142. You had just extracted the validation logic into a separate helper function.
              </p>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Futuristic Stats Tape */}
      <section className="w-full border-y border-white/5 bg-white/[0.02] backdrop-blur-sm z-10 relative overflow-hidden">
        <div className="max-w-7xl mx-auto py-12 px-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-4 divide-y md:divide-y-0 md:divide-x divide-white/10">
            {stats.map(({ value, label }, i) => (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                key={label}
                className="text-center pt-8 md:pt-0 first:pt-0"
              >
                <div className="text-4xl md:text-5xl font-bold font-mono mb-3 text-transparent bg-clip-text bg-gradient-to-b from-white to-zinc-500">
                  {value}
                </div>
                <div className="text-xs text-zinc-500 uppercase tracking-widest font-mono max-w-[200px] mx-auto leading-relaxed">{label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Bento Grid Features */}
      <section id="features" className="py-24 md:py-32 px-6 w-full max-w-7xl mx-auto z-10">
        <div className="text-center mb-16 md:mb-24">
          <p className="text-purple-400 font-mono text-xs tracking-widest uppercase mb-3 drop-shadow-[0_0_10px_rgba(168,85,247,0.5)]">The Architecture</p>
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight">Intelligence at every layer.</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
          {features.map(({ icon: Icon, title, desc }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              whileHover={{ y: -5 }}
              className="relative p-[1px] rounded-2xl overflow-hidden group bg-gradient-to-b from-white/10 to-transparent"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="h-full bg-black/80 backdrop-blur-xl rounded-2xl p-8 relative z-10 border border-white/5 group-hover:bg-black/60 transition-colors">
                <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-purple-500/20 group-hover:text-purple-300 transition-all border border-white/10">
                  <Icon size={20} className="text-white/70 group-hover:text-purple-300" />
                </div>
                <h3 className="text-xl font-semibold mb-3 tracking-tight">{title}</h3>
                <p className="text-zinc-400 leading-relaxed font-light">{desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Tech Stack Glowing Marquee / Grid */}
      <section id="stack" className="py-24 px-6 w-full border-t border-white/5 relative z-10 bg-black/50">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-purple-500/20 to-transparent" />

        <div className="max-w-6xl mx-auto text-center">
          <p className="text-xs font-mono uppercase tracking-widest text-zinc-500 mb-4">Enterprise Grade Infrastructure</p>
          <h2 className="text-3xl font-bold mb-16 tracking-tight">Built on the bleeding edge.</h2>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: Code2, label: "Next.js 14", sub: "React Server Components" },
              { icon: Database, label: "Qdrant", sub: "Vector Search Engine" },
              { icon: Brain, label: "Llama 3", sub: "Via Groq LPU API" },
              { icon: Terminal, label: "FastAPI", sub: "High-perf Async Python" },
              { icon: GitBranch, label: "NetworkX", sub: "Structural Code Graphs" },
              { icon: Zap, label: "Tree-sitter", sub: "AST Syntax Parsing" },
              { icon: Bookmark, label: "React Three Fiber", sub: "WebGL Rendered UI" },
              { icon: Search, label: "Framer Motion", sub: "Hardware Accel Animations" },
            ].map(({ icon: Icon, label, sub }, i) => (
              <motion.div
                key={label}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="flex flex-col items-center justify-center p-6 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
              >
                <Icon size={24} strokeWidth={1.5} className="text-zinc-500 mb-4" />
                <p className="text-sm font-medium text-zinc-200">{label}</p>
                <p className="text-[10px] text-zinc-500 font-mono mt-1 opacity-80">{sub}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="py-32 px-6 w-full max-w-4xl mx-auto text-center z-10 relative">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-[300px] bg-blue-600/10 blur-[100px] rounded-full pointer-events-none" />
        <h2 className="text-4xl md:text-6xl font-bold tracking-tighter mb-6">Gain perfect recall.</h2>
        <p className="text-zinc-400 mb-10 text-lg mx-auto max-w-xl font-light">
          ContextKeeper integrates with your local environment to save hours of re-onboarding overhead.
        </p>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-3 bg-white text-black font-semibold px-8 py-4 rounded-full hover:scale-105 transition-transform"
        >
          Initialize Workspace
          <ChevronRight size={16} />
        </Link>
      </section>

      {/* Minimalism strict Footer */}
      <footer className="w-full border-t border-white/5 py-8 z-10 bg-black">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-zinc-500">
            <Terminal size={12} strokeWidth={2.5} />
            <span className="font-semibold text-xs tracking-wide">CONTEXTKEEPER</span>
          </div>
          <p className="text-[10px] uppercase tracking-widest font-mono text-zinc-600">
            © 2026 · Built exclusively for AI for Bharat.
          </p>
        </div>
      </footer>
    </div>
  );
}
