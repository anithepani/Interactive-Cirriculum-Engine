"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Compass, Network, RefreshCw } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import RecommendationGrid from "@/components/RecommendationGrid";

export default function DiscoverPage() {
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);

  const handleGenerate = () => {
    setGenerating(true);
    // Simulate graph traversal time
    setTimeout(() => {
      setGenerating(false);
      setGenerated(true);
    }, 4500); // 4.5 seconds for the cool animation
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-6xl space-y-8">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
            <Compass className="h-6 w-6" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-bold text-ink">Discover</h1>
            <p className="text-sm text-ink-soft">AI-Powered Curriculum Recommendations</p>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {!generated && !generating && (
            <motion.div
              key="cta"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex flex-col items-center justify-center rounded-[2.5rem] border border-ink/5 bg-gradient-to-br from-indigo-600 via-purple-600 to-fuchsia-600 p-12 text-center text-white shadow-xl"
            >
              <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-white/10 backdrop-blur-md">
                <Network className="h-10 w-10 text-white" />
              </div>
              <h2 className="font-display text-3xl font-bold tracking-tight md:text-4xl">
                Find Your Next Curriculum
              </h2>
              <p className="mt-4 max-w-lg text-lg text-white/80">
                Our Unified Knowledge Graph analyzes your recent progress, weak points, and interests to generate the perfect learning path.
              </p>
              <button
                onClick={handleGenerate}
                className="mt-8 flex items-center gap-2 rounded-full bg-white px-8 py-4 font-bold text-indigo-600 shadow-lg transition hover:scale-105 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
              >
                <Sparkles className="h-5 w-5" />
                Generate Personalized Path
              </button>
            </motion.div>
          )}

          {generating && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex min-h-[400px] flex-col items-center justify-center rounded-[2.5rem] border border-ink/5 bg-white p-12 shadow-sm"
            >
              {/* Clean Graph Simulation */}
              <div className="relative flex h-48 w-full max-w-md items-center justify-center">
                {/* Center Node (AI) */}
                <motion.div
                  animate={{ scale: [1, 1.2, 1], boxShadow: ["0px 0px 0px rgba(79, 70, 229, 0)", "0px 0px 30px rgba(79, 70, 229, 0.4)", "0px 0px 0px rgba(79, 70, 229, 0)"] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                  className="absolute z-10 flex h-16 w-16 items-center justify-center rounded-full bg-indigo-600 text-white shadow-lg"
                >
                  <Network className="h-8 w-8" />
                </motion.div>

                {/* Left Node (Weakness) */}
                <motion.div
                  initial={{ x: -100, opacity: 0 }}
                  animate={{ x: -80, opacity: 1 }}
                  transition={{ duration: 0.5 }}
                  className="absolute left-0 z-0 flex flex-col items-center gap-2"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-rose-200 bg-rose-50 text-rose-500">
                    <span className="text-xs font-bold">Failed</span>
                  </div>
                </motion.div>

                {/* Right Node (Interest) */}
                <motion.div
                  initial={{ x: 100, opacity: 0 }}
                  animate={{ x: 80, opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  className="absolute right-0 z-0 flex flex-col items-center gap-2"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-emerald-200 bg-emerald-50 text-emerald-500">
                    <span className="text-xs font-bold">Goal</span>
                  </div>
                </motion.div>

                {/* Connecting Lines */}
                <svg className="absolute inset-0 h-full w-full" style={{ zIndex: 0 }}>
                  <motion.line
                    x1="25%"
                    y1="50%"
                    x2="50%"
                    y2="50%"
                    stroke="#4F46E5"
                    strokeWidth="3"
                    strokeDasharray="5,5"
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 0.5 }}
                    transition={{ duration: 1, repeat: Infinity }}
                  />
                  <motion.line
                    x1="75%"
                    y1="50%"
                    x2="50%"
                    y2="50%"
                    stroke="#4F46E5"
                    strokeWidth="3"
                    strokeDasharray="5,5"
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 0.5 }}
                    transition={{ duration: 1, delay: 0.5, repeat: Infinity }}
                  />
                </svg>
              </div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="mt-8 flex flex-col items-center text-center"
              >
                <h3 className="font-display text-xl font-bold text-ink">Analyzing Knowledge Graph...</h3>
                <div className="mt-4 flex flex-col gap-2 text-sm text-ink-soft">
                  <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>✓ Extracting weak concepts</motion.p>
                  <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.5 }}>✓ Mapping interest vectors</motion.p>
                  <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 2.5 }}>✓ Calculating pgvector cosine similarity</motion.p>
                  <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 3.5 }}>✓ Finding foundational prerequisites</motion.p>
                </div>
              </motion.div>
            </motion.div>
          )}

          {generated && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="flex items-center justify-between">
                <h2 className="font-display text-xl font-bold text-ink">Your Personalized Path</h2>
                <button
                  onClick={() => setGenerated(false)}
                  className="flex items-center gap-2 rounded-lg text-sm font-medium text-ink-soft hover:text-indigo-600 transition"
                >
                  <RefreshCw className="h-4 w-4" />
                  Regenerate
                </button>
              </div>
              
              <RecommendationGrid />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </AppLayout>
  );
}
