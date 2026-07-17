"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import AppLayout from "@/components/layout/AppLayout";
import LoadingSpinner from "@/components/LoadingSpinner";
import { authFetcher } from "@/lib/auth";
import type { CurriculumSummary } from "@/lib/types";
import { staggerContainer } from "@/lib/motion";
import { BookOpen, MonitorPlay, Palette, Briefcase, Brain, Code } from "lucide-react";

// Intelligent category inferrence based on video title keywords
const inferCategory = (title: string) => {
  const t = title.toLowerCase();
  if (t.includes("react") || t.includes("python") || t.includes("code") || t.includes("js") || t.includes("html") || t.includes("css") || t.includes("java")) {
    return { name: "Programming", icon: Code, color: "text-blue-600", bg: "bg-blue-50", fill: "bg-blue-600" };
  }
  if (t.includes("design") || t.includes("ui") || t.includes("ux") || t.includes("figma") || t.includes("photoshop")) {
    return { name: "UI/UX Design", icon: Palette, color: "text-fuchsia-600", bg: "bg-fuchsia-50", fill: "bg-fuchsia-600" };
  }
  if (t.includes("business") || t.includes("finance") || t.includes("marketing") || t.includes("money") || t.includes("startup")) {
    return { name: "Business", icon: Briefcase, color: "text-emerald-600", bg: "bg-emerald-50", fill: "bg-emerald-600" };
  }
  if (t.includes("mind") || t.includes("psychology") || t.includes("health") || t.includes("stress") || t.includes("habit")) {
    return { name: "Personal Growth", icon: Brain, color: "text-rose-600", bg: "bg-rose-50", fill: "bg-rose-600" };
  }
  return { name: "General Learning", icon: MonitorPlay, color: "text-indigo-600", bg: "bg-indigo-50", fill: "bg-indigo-600" };
};

export default function ProgressPage() {
  const { data, error, isLoading } = useSWR<CurriculumSummary[]>("/api/v1/curricula", authFetcher);

  const stats = useMemo(() => {
    if (!data) return { categories: [], totalHours: 0, completed: 0 };
    
    let totalHours = 0;
    let completed = 0;
    const categoryMap: Record<string, any> = {};

    data.forEach(item => {
      if (item.status === "ready") completed++;
      // Assume each curriculum is roughly 1.5 hours of learning for demonstration
      totalHours += 1.5; 
      
      const cat = inferCategory(item.title);
      if (!categoryMap[cat.name]) {
        categoryMap[cat.name] = { ...cat, count: 0, items: [] };
      }
      categoryMap[cat.name].count++;
      categoryMap[cat.name].items.push(item);
    });

    const categories = Object.values(categoryMap).sort((a, b) => b.count - a.count);
    
    return { categories, totalHours: Math.round(totalHours), completed };
  }, [data]);

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
                    <p className="font-display text-3xl font-black text-ink">{data?.length || 0}</p>
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
                    <p className="font-display text-3xl font-black text-ink">{stats.completed * 3}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Categorical Breakdown */}
            <div>
              <h2 className="mb-6 font-display text-xl font-bold text-ink">Learning Categories</h2>
              <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="grid grid-cols-1 gap-6 md:grid-cols-2">
                {stats.categories.map((cat: any, index: number) => {
                  const percentage = Math.round((cat.count / (data?.length || 1)) * 100);
                  return (
                    <motion.div 
                      key={cat.name} 
                      custom={index}
                      variants={{
                        hidden: { opacity: 0, y: 20 },
                        visible: (i) => ({
                          opacity: 1,
                          y: 0,
                          transition: { delay: i * 0.1, duration: 0.5 }
                        })
                      }}
                      className="rounded-[2rem] border border-ink/5 bg-white p-6 shadow-sm"
                    >
                      <div className="mb-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${cat.bg} ${cat.color}`}>
                            <cat.icon className="h-5 w-5" />
                          </div>
                          <div>
                            <h3 className="font-display font-bold text-ink">{cat.name}</h3>
                            <p className="text-xs text-ink-soft">{cat.count} curricula</p>
                          </div>
                        </div>
                        <span className="font-display text-xl font-bold text-ink">{percentage}%</span>
                      </div>
                      
                      {/* Progress bar */}
                      <div className="h-2.5 w-full rounded-full bg-ink/5 overflow-hidden">
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${percentage}%` }}
                          transition={{ duration: 1, delay: 0.5 + index * 0.1, ease: "easeOut" }}
                          className={`h-full rounded-full ${cat.fill}`}
                        />
                      </div>
                    </motion.div>
                  );
                })}
              </motion.div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
