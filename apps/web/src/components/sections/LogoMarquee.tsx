"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Box,
  Database,
  Layers,
  Server,
  Cpu,
  Container as ContainerIcon,
} from "lucide-react";
import { MARQUEE_LOGOS } from "@/lib/data";
import { fadeUp, viewportOnce } from "@/lib/motion";

const ICON_MAP: Record<string, React.ReactNode> = {
  judge0: <Cpu className="h-6 w-6" />,
  fastapi: <Server className="h-6 w-6" />,
  nextjs: <Layers className="h-6 w-6" />,
  celery: <Box className="h-6 w-6" />,
  redis: <Database className="h-6 w-6" />,
  pytorch: <Cpu className="h-6 w-6" />,
  postgresql: <Database className="h-6 w-6" />,
  docker: <ContainerIcon className="h-6 w-6" />,
};

function MarqueeTrack() {
  const items = [...MARQUEE_LOGOS, ...MARQUEE_LOGOS];
  return (
    <div className="flex w-max motion-safe:animate-marquee gap-16">
      {items.map((logo, i) => (
        <div
          key={`${logo.name}-${i}`}
          className="flex items-center gap-3 grayscale opacity-50 transition hover:grayscale-0 hover:opacity-100"
        >
          {ICON_MAP[logo.name]}
          <span className="font-mono text-sm font-semibold text-ink">{logo.label}</span>
        </div>
      ))}
    </div>
  );
}

export default function LogoMarquee() {
  return (
    <section className="overflow-hidden bg-canvas px-6 py-16">
      <motion.div
        className="mx-auto max-w-container text-center"
        initial="hidden"
        whileInView="visible"
        viewport={viewportOnce}
        variants={fadeUp}
        custom={0}
      >
        <p className="text-ink-soft">Trusted by the best scaling teams.</p>
        <div className="mt-10 overflow-hidden">
          <MarqueeTrack />
        </div>
      </motion.div>
    </section>
  );
}
