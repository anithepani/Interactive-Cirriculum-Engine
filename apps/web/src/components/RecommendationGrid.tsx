"use client";

import React from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { ExternalLink, Sparkles, AlertCircle, Compass, CheckCircle2 } from "lucide-react";
import { authFetcher } from "@/lib/auth";

export interface RecommendationCardData {
  id: string;
  title: string;
  url: string;
  tags: string[];
  badge: string;
  reason: string;
  score: number;
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  show: { opacity: 1, y: 0, scale: 1, transition: { type: "spring", stiffness: 200, damping: 20 } },
  hover: { y: -5, scale: 1.02, transition: { duration: 0.2 } },
};

export default function RecommendationGrid() {
  const { data: recommendations, error, isLoading } = useSWR<RecommendationCardData[]>(
    "/api/v1/recommendations/feed",
    authFetcher
  );

  if (error) {
    return (
      <div className="flex h-32 items-center justify-center rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400">
        <AlertCircle className="w-5 h-5 mr-2" />
        Failed to load recommendations
      </div>
    );
  }

  if (isLoading || !recommendations) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="relative w-12 h-12">
          <div className="absolute inset-0 rounded-full border-t-2 border-accent-lime animate-spin"></div>
          <div className="absolute inset-2 rounded-full border-r-2 border-accent-purple animate-spin-reverse"></div>
        </div>
      </div>
    );
  }

  if (recommendations.length === 0) {
    return null;
  }

  const getBadgeIcon = (badge: string) => {
    switch (badge) {
      case "High Priority Fix": return <AlertCircle className="w-4 h-4 mr-1" />;
      case "Next Step": return <Sparkles className="w-4 h-4 mr-1" />;
      case "Discovery": return <Compass className="w-4 h-4 mr-1" />;
      default: return <CheckCircle2 className="w-4 h-4 mr-1" />;
    }
  };

  const getBadgeColor = (badge: string) => {
    switch (badge) {
      case "High Priority Fix": return "bg-rose-50 text-rose-600 border-rose-200";
      case "Next Step": return "bg-indigo-50 text-indigo-600 border-indigo-200";
      case "Discovery": return "bg-blue-50 text-blue-600 border-blue-200";
      default: return "bg-emerald-50 text-emerald-600 border-emerald-200"; // Foundational
    }
  };

  return (
    <div className="mb-10 w-full">
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-display text-2xl font-bold text-ink flex items-center">
          <Sparkles className="w-6 h-6 mr-2 text-indigo-500" />
          AI Recommendations
        </h2>
        <div className="px-3 py-1 text-xs font-medium bg-indigo-50 border border-indigo-100 rounded-full text-indigo-600">
          Powered by Unified Knowledge Graph
        </div>
      </div>
      
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <AnimatePresence>
          {recommendations.map((item) => (
            <motion.a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              variants={cardVariants}
              whileHover="hover"
              className="group relative flex flex-col justify-between p-6 rounded-[2.5rem] bg-white border border-ink/5 shadow-sm overflow-hidden cursor-pointer"
            >
              {/* Animated Gradient Glow */}
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-50/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
              
              <div className="relative z-10">
                <div className="flex items-center justify-between mb-4">
                  <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getBadgeColor(item.badge)}`}>
                    {getBadgeIcon(item.badge)}
                    {item.badge}
                  </span>
                  
                  {item.score > 0 && (
                    <span className="text-xs font-mono text-ink-soft/60">
                      Match: {(item.score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>

                <h3 className="text-xl font-bold text-ink mb-2 leading-tight group-hover:text-indigo-600 transition-colors">
                  {item.title}
                </h3>
                
                <p className="text-sm text-ink-soft mb-6">
                  {item.reason}
                </p>
              </div>

              <div className="relative z-10 flex items-end justify-between mt-auto pt-4 border-t border-ink/5">
                <div className="flex flex-wrap gap-2">
                  {item.tags?.slice(0, 3).map(tag => (
                    <span key={tag} className="px-2 py-0.5 text-[10px] uppercase tracking-wider font-semibold rounded bg-ink/5 text-ink-soft">
                      {tag}
                    </span>
                  ))}
                  {item.tags?.length > 3 && (
                    <span className="px-2 py-0.5 text-[10px] uppercase tracking-wider font-semibold rounded bg-ink/5 text-ink-soft">
                      +{item.tags.length - 3}
                    </span>
                  )}
                </div>
                <div className="w-8 h-8 rounded-full bg-ink/5 flex items-center justify-center group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors shrink-0 text-ink-soft">
                  <ExternalLink className="w-4 h-4" />
                </div>
              </div>
            </motion.a>
          ))}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
