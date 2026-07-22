"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import AppLayout from "@/components/layout/AppLayout";
import LoadingSpinner from "@/components/LoadingSpinner";
import { authFetcher } from "@/lib/auth";
import type { CurriculumSummary, StatsOverview } from "@/lib/types";
import { staggerContainer } from "@/lib/motion";
import { BookOpen, MonitorPlay, Palette, Briefcase, Brain, Code, ChevronDown, ChevronUp, PlayCircle } from "lucide-react";
import Link from "next/link";

// Intelligent category inferrence based on video title keywords
// Maps a backend category label (or a raw title) onto the local icon/color
// palette. Matches the backend's category names first, then falls back to
// keyword sniffing so the mapping still works for arbitrary titles.
const inferCategory = (label: string) => {
  const t = label.toLowerCase();
  if (t.includes("program") || t.includes("react") || t.includes("python") || t.includes("code") || t.includes("js") || t.includes("html") || t.includes("css") || t.includes("java")) {
    return { name: "Programming", icon: Code, color: "text-sky-600", bg: "bg-sky-50", fill: "bg-sky-600" };
  }
  if (t.includes("data") || t.includes("ai") || t.includes("ml") || t.includes("machine")) {
    return { name: "Data & AI", icon: Brain, color: "text-rose-600", bg: "bg-rose-50", fill: "bg-rose-600" };
  }
  if (t.includes("design") || t.includes("ui") || t.includes("ux") || t.includes("figma") || t.includes("photoshop")) {
    return { name: "UI/UX Design", icon: Palette, color: "text-fuchsia-600", bg: "bg-fuchsia-50", fill: "bg-fuchsia-600" };
  }
  if (t.includes("business") || t.includes("finance") || t.includes("marketing") || t.includes("money") || t.includes("startup")) {
    return { name: "Business", icon: Briefcase, color: "text-emerald-600", bg: "bg-emerald-50", fill: "bg-emerald-600" };
  }
  return { name: "General Learning", icon: MonitorPlay, color: "text-indigo-600", bg: "bg-indigo-50", fill: "bg-indigo-600" };
};

export default function ProgressPage() {
  const { data, error, isLoading } = useSWR<CurriculumSummary[]>("/api/v1/curricula", authFetcher);
  // Live progress breakdown from the backend (Block D): real hours, exercise
  // counts and concept-weighted categories rather than the old client-side
  // heuristics (1.5h/course, count*3 exercises, title keywords).
  const { data: progress } = useSWR<StatsOverview>("/api/v1/stats/progress", authFetcher);

  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  const stats = useMemo(() => {
    // Map backend categories onto the local icon/color palette. `inferCategory`
    // keys off the category label so styling stays consistent with the cards.
    const backendCats = progress?.categories ?? [];
    const categories = backendCats.map((c) => {
      const meta = inferCategory(c.category);
      return { ...meta, name: c.category, count: c.count, percent: c.percent };
    });

    return {
      categories,
      totalHours: progress?.hours_learned ?? 0,
      totalCurricula: progress?.total_curricula ?? data?.length ?? 0,
      completedExercises: progress?.completed_exercises ?? 0,
      correctExercises: progress?.correct_exercises ?? 0,
    };
  }, [progress, data]);

  // Construct conic-gradient for the beautiful pie chart
  const pieGradient = useMemo(() => {
    let currentPercent = 0;
    const stops = stats.categories.map(cat => {
      // Find matching tailwind color hex (approximate based on the palette)
      let hex = "#4f46e5"; // indigo-600
      if (cat.color.includes("sky")) hex = "#0284c7";
      else if (cat.color.includes("rose")) hex = "#e11d48";
      else if (cat.color.includes("fuchsia")) hex = "#c026d3";
      else if (cat.color.includes("emerald")) hex = "#059669";
      
      const start = currentPercent;
      currentPercent += cat.percent;
      return `${hex} ${start}% ${currentPercent}%`;
    });
    return `conic-gradient(${stops.join(", ")})`;
  }, [stats.categories]);

  return (
    <AppLayout>
      <div className="mx-auto max-w-5xl">
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-ink">Progress Report</h1>
          <p className="mt-2 text-ink-soft">
            Track your skill acquisition and learning categories.
          </p>
        </div>

        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <LoadingSpinner size={32} />
          </div>
        ) : error ? (
          <div className="rounded-[2rem] border border-rose-200 bg-rose-50 p-6 text-rose-700">
            Failed to load progress data.
          </div>
        ) : (
          <div className="space-y-8">
            {/* Top Stats */}
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-[2rem] border border-ink/5 bg-white p-6 shadow-sm">
                <div className="flex items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                    <BookOpen className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-ink-soft">Total Curricula</p>
                    <p className="font-display text-3xl font-black text-ink">{stats.totalCurricula}</p>
                  </div>
                </div>
              </div>
              
              <div className="rounded-[2rem] border border-ink/5 bg-white p-6 shadow-sm">
                <div className="flex items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                    <MonitorPlay className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-ink-soft">Hours Learned</p>
                    <p className="font-display text-3xl font-black text-ink">{stats.totalHours}<span className="text-base font-medium text-ink-soft">h</span></p>
                  </div>
                </div>
              </div>
              
              <div className="rounded-[2rem] border border-ink/5 bg-white p-6 shadow-sm sm:col-span-2 lg:col-span-1">
                <div className="flex items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-fuchsia-50 text-fuchsia-600">
                    <Brain className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-ink-soft">Completed Exercises</p>
                    <p className="font-display text-3xl font-black text-ink">{stats.completedExercises}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Categorical Breakdown & Pie Chart */}
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <h2 className="mb-6 font-display text-xl font-bold text-ink">Learning Categories</h2>
                <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="flex flex-col gap-4">
                  {stats.categories.map((cat, index: number) => {
                    const percentage = Math.round(cat.percent);
                    const isExpanded = expandedCategory === cat.name;
                    // Find related videos for this category
                    const relatedVideos = (data || []).filter(item => {
                      // Use backend category if available (this logic mirrors what's built in the Stats API)
                      // If stats aren't perfectly synced yet, we fallback to inferCategory on the title
                      const mapped = inferCategory(item.title);
                      return mapped.name === cat.name;
                    });

                    return (
                      <motion.div 
                        key={cat.name} 
                        custom={index}
                        variants={{
                          hidden: { opacity: 0, y: 10 },
                          visible: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.1, duration: 0.4 } })
                        }}
                        className="overflow-hidden rounded-[2rem] border border-ink/5 bg-white shadow-sm transition hover:border-ink/10"
                      >
                        <button 
                          onClick={() => setExpandedCategory(isExpanded ? null : cat.name)}
                          className="flex w-full items-center justify-between p-6 focus:outline-none"
                        >
                          <div className="flex items-center gap-4">
                            <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${cat.bg} ${cat.color}`}>
                              <cat.icon className="h-5 w-5" />
                            </div>
                            <div className="text-left">
                              <h3 className="font-display font-bold text-ink">{cat.name}</h3>
                              <p className="text-xs font-medium text-ink-soft">
                                {cat.count} {cat.count === 1 ? 'concept' : 'concepts'} • {percentage}%
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-4">
                            <span className="hidden rounded-full bg-ink/5 px-3 py-1 text-xs font-semibold text-ink-soft sm:inline-block">
                              {relatedVideos.length} {relatedVideos.length === 1 ? 'Video' : 'Videos'}
                            </span>
                            <div className="text-ink-soft transition-transform duration-200">
                              {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                            </div>
                          </div>
                        </button>
                        
                        {isExpanded && (
                          <div className="border-t border-ink/5 bg-slate-50 p-6 pt-4">
                            <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-ink-soft">Related Videos You Watched</h4>
                            {relatedVideos.length === 0 ? (
                              <p className="text-sm text-ink-soft">No videos matched this category yet.</p>
                            ) : (
                              <div className="flex flex-col gap-2">
                                {relatedVideos.map(video => (
                                  <Link 
                                    key={video.id} 
                                    href={`/curriculum/${video.id}`}
                                    className="flex items-center gap-3 rounded-xl border border-ink/5 bg-white p-3 shadow-sm transition hover:border-indigo-200 hover:bg-indigo-50"
                                  >
                                    <PlayCircle className="h-5 w-5 shrink-0 text-indigo-500" />
                                    <span className="truncate text-sm font-semibold text-ink">{video.title}</span>
                                  </Link>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </motion.div>
                    );
                  })}
                </motion.div>
              </div>

              {/* Pie Chart Section */}
              <div className="lg:col-span-1">
                <h2 className="mb-6 font-display text-xl font-bold text-ink">Topic Distribution</h2>
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  className="rounded-[2.5rem] border border-ink/5 bg-white p-8 shadow-sm flex flex-col items-center"
                >
                  <div className="relative flex h-56 w-56 items-center justify-center">
                    {/* The Pie/Donut background */}
                    <motion.div 
                      initial={{ rotate: -90, opacity: 0 }}
                      animate={{ rotate: 0, opacity: 1 }}
                      transition={{ duration: 1, ease: "easeOut" }}
                      className="absolute inset-0 rounded-full shadow-md"
                      style={{ background: pieGradient }}
                    />
                    {/* Inner cutout to make it a thick Donut */}
                    <div className="absolute inset-6 rounded-full bg-white shadow-inner flex items-center justify-center">
                      <div className="text-center">
                        <span className="block font-display text-3xl font-black text-ink">100<span className="text-lg">%</span></span>
                        <span className="block text-[10px] uppercase font-bold text-ink-soft tracking-wider mt-1">Total Focus</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-8 flex w-full flex-col gap-4">
                    {stats.categories.map((cat, idx) => (
                      <motion.div 
                        key={cat.name} 
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 + (idx * 0.1) }}
                        className="group flex items-center justify-between text-sm rounded-xl p-2 transition hover:bg-ink/5 cursor-default"
                      >
                        <div className="flex items-center gap-3">
                          <span className={`h-4 w-4 rounded-full ${cat.fill} shadow-sm transition-transform group-hover:scale-125`} />
                          <span className="font-semibold text-ink-soft group-hover:text-ink transition">{cat.name}</span>
                        </div>
                        <span className="font-black text-ink">{Math.round(cat.percent)}%</span>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
