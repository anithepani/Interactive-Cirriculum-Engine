"use client";

import { Dumbbell, Video, AlertTriangle, RefreshCw } from "lucide-react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import AppLayout from "@/components/layout/AppLayout";
import CurriculumCard from "@/components/CurriculumCard";
import LoadingSpinner from "@/components/LoadingSpinner";
import { authFetcher } from "@/lib/auth";
import type { CurriculumSummary } from "@/lib/types";
import { staggerContainer } from "@/lib/motion";

const POLL_INTERVAL = 5_000;

const refreshInterval = (latest?: CurriculumSummary[]) => {
  if (!latest || latest.length === 0) return 0;
  const pending = latest.some(
    (c) => c.status !== "ready" && c.status !== "failed"
  );
  return pending ? POLL_INTERVAL : 0;
};

export default function ExercisesPage() {
  const { data, error, isLoading, isValidating } =
    useSWR<CurriculumSummary[]>("/api/v1/curricula", authFetcher, {
      refreshInterval,
    });

  return (
    <AppLayout>
      <div className="mx-auto max-w-5xl">
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-ink">Interactive Exercises</h1>
          <p className="mt-2 text-ink-soft">
            Select a curriculum below to dive directly into its generated practice problems and challenges.
          </p>
        </div>

        <div className="mt-4">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="font-display text-xl font-semibold text-ink">Your Curricula</h2>
            <div className="flex items-center gap-2">
              <AnimatePresence>
                {isValidating && !isLoading && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center gap-1 text-xs text-ink-soft">
                    <RefreshCw className="h-3 w-3 animate-spin" />
                    Syncing
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-64 animate-pulse rounded-[2rem] border border-ink/10 bg-ink/5" style={{ animationDelay: `${i * 0.1}s` }} />
              ))}
            </div>
          ) : error ? (
            <div className="flex items-start gap-4 rounded-[2rem] border border-rose-200 bg-rose-50 px-6 py-5 text-rose-700">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" />
              <div>
                <p className="font-semibold text-rose-700">Failed to load curricula</p>
                <p className="mt-1 text-sm text-rose-600">{(error as Error).message}</p>
              </div>
            </div>
          ) : !data || data.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center justify-center gap-6 rounded-[2rem] border border-ink/10 bg-white py-20 px-8 text-center shadow-sm"
            >
              <motion.div
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                className="flex h-20 w-20 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-500"
              >
                <Dumbbell className="h-10 w-10" />
              </motion.div>
              <div className="max-w-xs space-y-2">
                <p className="font-display text-xl font-bold text-ink">No exercises yet</p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  Upload a video in the dashboard to automatically generate your first interactive exercises.
                </p>
              </div>
            </motion.div>
          ) : (
            <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {data.map((curriculum, index) => (
                <CurriculumCard
                  key={curriculum.id}
                  curriculum={curriculum}
                  index={index}
                  hrefPrefix="/exercises"
                />
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
