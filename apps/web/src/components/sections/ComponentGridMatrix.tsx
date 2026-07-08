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

        <motion.div
          className="absolute left-1/2 top-1/2 w-80 max-w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-xl2 bg-white p-6 shadow-2xl"
          whileHover={{ y: -4 }}
        >
          <div className="flex items-center gap-3">
            <Avatar>
              <AvatarFallback>TW</AvatarFallback>
            </Avatar>
            <div>
              <p className="font-semibold">{COMPONENT_GRID_PROFILE.name}</p>
              <p className="font-mono text-xs text-ink-soft">{COMPONENT_GRID_PROFILE.caption}</p>
            </div>
          </div>

          <pre className="mt-4 overflow-x-auto rounded-md bg-ink p-3 font-mono text-xs text-lime">
            {COMPONENT_GRID_PROFILE.codeSnippet}
          </pre>

          <div className="mt-4 flex items-center gap-3">
            <button
              type="button"
              onClick={() => setLiked((v) => !v)}
              className="rounded-full p-2 hover:bg-ink/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30"
              aria-label={liked ? "Unlike" : "Like"}
              aria-pressed={liked}
            >
              <Heart
                className={`h-5 w-5 ${liked ? "fill-hotpink text-hotpink" : "text-ink"}`}
              />
            </button>
            <Badge variant="lime" className="gap-1">
              <BadgeCheck className="h-3 w-3" />
              Verified
            </Badge>
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}
