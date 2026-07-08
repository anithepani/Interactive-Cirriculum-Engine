"use client";

import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, Play } from "lucide-react";
import { useState } from "react";
import { INSTRUCTOR_SPOTLIGHT } from "@/lib/data";
import { fadeUp, staggerContainer, viewportOnce } from "@/lib/motion";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";

export default function InstructorSpotlight() {
  const [slide, setSlide] = useState(0);
  const slides = [
    "AI dev environment with checkpoint overlays active",
    "Curriculum map showing segmented concept nodes",
  ];

  return (
    <section
      id="instructor-spotlight"
      className="bg-canvas px-6 py-16 md:py-24"
    >
      <motion.div
        className="mx-auto max-w-container"
        variants={staggerContainer}
        initial="hidden"
        whileInView="visible"
        viewport={viewportOnce}
      >
        <motion.p
          variants={fadeUp}
          custom={0}
          className="font-mono text-sm tracking-widest text-ink-soft"
        >
          {INSTRUCTOR_SPOTLIGHT.label}
        </motion.p>
        <motion.h2
          variants={fadeUp}
          custom={1}
          className="mt-3 font-display text-4xl font-bold text-ink md:text-5xl"
        >
          {INSTRUCTOR_SPOTLIGHT.headline}
        </motion.h2>

        <motion.div
          variants={fadeUp}
          custom={2}
          className="relative mt-10 h-[320px] overflow-hidden rounded-xl2 bg-surfaceDark md:h-[480px]"
        >
          <div
            className="absolute inset-0 bg-gradient-to-br from-blue/40 via-surfaceDark to-surfaceDark"
            aria-hidden="true"
          />
          <div className="absolute inset-0 bg-blue/30 mix-blend-multiply" aria-hidden="true" />
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="max-w-md px-6 text-center text-sm text-white/70 md:text-base">
              {slides[slide]} — ICE segmentation pipeline rendering interactive checkpoints over tutorial footage.
            </p>
          </div>

          <div className="absolute left-4 top-4 md:left-6 md:top-6">
            <Tabs defaultValue="overview">
              <TabsList className="border border-white/20 bg-white/10 backdrop-blur-md">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="curriculum">Curriculum Map</TabsTrigger>
              </TabsList>
              <TabsContent value="overview" className="sr-only">Overview selected</TabsContent>
              <TabsContent value="curriculum" className="sr-only">Curriculum Map selected</TabsContent>
            </Tabs>
          </div>

          <div className="absolute bottom-4 left-4 right-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between md:bottom-6 md:left-6 md:right-6">
            <Button className="w-fit rounded-full bg-white text-ink hover:bg-white/90">
              <span className="mr-2 flex h-8 w-8 items-center justify-center rounded-full bg-ink text-white">
                <Play className="h-4 w-4 fill-white" />
              </span>
              {INSTRUCTOR_SPOTLIGHT.cta}
            </Button>

            <div className="flex gap-2 self-end sm:self-auto">
              <motion.button
                type="button"
                onClick={() => setSlide((s) => (s === 0 ? 1 : 0))}
                className="flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-white/10 backdrop-blur focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                aria-label="Previous slide"
              >
                <ChevronLeft className="h-5 w-5 text-white" />
              </motion.button>
              <motion.button
                type="button"
                onClick={() => setSlide((s) => (s === 0 ? 1 : 0))}
                className="flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-white/10 backdrop-blur focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                aria-label="Next slide"
              >
                <ChevronRight className="h-5 w-5 text-white" />
              </motion.button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}
