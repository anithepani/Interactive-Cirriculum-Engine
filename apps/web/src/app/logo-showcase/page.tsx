"use client";

import { BrainCircuit, Hexagon, Flame, Sparkles } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

export default function LogoShowcase() {
  return (
    <div className="min-h-screen bg-white p-12">
      <div className="mx-auto max-w-4xl space-y-12">
        <div>
          <h1 className="font-display text-4xl font-bold text-ink">Logo Options</h1>
          <p className="mt-2 text-ink-soft">
            Here are three vector-based directions for the new ICE logo. They maintain the premium, high-performance aesthetic of the platform.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          {/* Option 1 */}
          <motion.div whileHover={{ scale: 1.02 }} className="flex flex-col items-center gap-6 rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
            <h2 className="font-display text-xl font-bold text-ink">Option 1: The AI Engine</h2>
            <div className="flex items-center gap-3">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/20">
                <BrainCircuit className="h-10 w-10" />
              </div>
              <span className="font-display text-4xl font-bold tracking-tight text-ink">ICE</span>
            </div>
            <p className="text-center text-sm text-ink-soft">Emphasizes the artificial intelligence and neural network core of the platform.</p>
          </motion.div>

          {/* Option 2 */}
          <motion.div whileHover={{ scale: 1.02 }} className="flex flex-col items-center gap-6 rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
            <h2 className="font-display text-xl font-bold text-ink">Option 2: The Foundation</h2>
            <div className="flex items-center gap-3">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-fuchsia-600 text-white shadow-lg shadow-fuchsia-600/20">
                <Hexagon className="h-10 w-10" />
              </div>
              <span className="font-display text-4xl font-bold tracking-tight text-ink">ICE</span>
            </div>
            <p className="text-center text-sm text-ink-soft">Emphasizes structured curriculum, building blocks, and modular learning.</p>
          </motion.div>

          {/* Option 3 */}
          <motion.div whileHover={{ scale: 1.02 }} className="flex flex-col items-center gap-6 rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
            <h2 className="font-display text-xl font-bold text-ink">Option 3: The Catalyst</h2>
            <div className="flex items-center gap-3">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-emerald-600 text-white shadow-lg shadow-emerald-600/20">
                <Flame className="h-10 w-10" />
              </div>
              <span className="font-display text-4xl font-bold tracking-tight text-ink">ICE</span>
            </div>
            <p className="text-center text-sm text-ink-soft">Emphasizes speed, interactivity, and maintaining learning streaks.</p>
          </motion.div>
        </div>

        <div className="mt-12 rounded-[2rem] border border-ink/10 bg-ink/5 p-8">
          <h2 className="font-display text-xl font-bold text-ink mb-4">Current Logo (For Comparison)</h2>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
              <Sparkles className="h-7 w-7" />
            </div>
            <span className="font-display text-2xl font-bold tracking-tight text-ink">ICE</span>
          </div>
        </div>

        <div className="pt-8">
          <Link href="/dashboard" className="text-indigo-600 hover:underline font-semibold">
            &larr; Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
