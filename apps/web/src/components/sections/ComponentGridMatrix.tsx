"use client";

import { motion } from "framer-motion";
import { BadgeCheck, Heart, Database, Box, Server, Cpu, Container } from "lucide-react";
import { useState } from "react";
import { COMPONENT_GRID_PROFILE, TOOL_BELT_ICONS } from "@/lib/data";
import { fadeUp, viewportOnce } from "@/lib/motion";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

const TOOL_ICONS: Record<string, React.ReactNode> = {
  Docker: <Container className="h-5 w-5" />,
  PostgreSQL: <Database className="h-5 w-5" />,
  Redis: <Database className="h-5 w-5" />,
  Celery: <Box className="h-5 w-5" />,
  FastAPI: <Server className="h-5 w-5" />,
  pgvector: <Cpu className="h-5 w-5" />,
};

export default function ComponentGridMatrix() {
  const [liked, setLiked] = useState(false);
  const beltItems = [...TOOL_BELT_ICONS, ...TOOL_BELT_ICONS];

  return (
    <section className="relative overflow-hidden bg-canvas px-6 py-16 md:py-24">
      <div className="overflow-hidden py-6">
        <div className="flex w-max motion-safe:animate-marqueeReverse gap-12">
          {beltItems.map((tool, i) => (
            <div key={`${tool}-${i}`} className="flex items-center gap-2 font-mono text-sm text-ink-soft">
              {TOOL_ICONS[tool]}
              {tool}
            </div>
          ))}
        </div>
      </div>

      <motion.div
        className="relative mx-auto mt-8 max-w-container"
        initial="hidden"
        whileInView="visible"
        viewport={viewportOnce}
        variants={fadeUp}
      >
        <div className="grid grid-cols-3 gap-3 md:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="aspect-[3/4] rounded-lg bg-ink/5"
              aria-hidden="true"
            />
          ))}
        </div>

      </motion.div>
    </section>
  );
}
