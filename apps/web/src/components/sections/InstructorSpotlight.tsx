"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { ChevronLeft, ChevronRight, Play, Cpu, Code2 } from "lucide-react";
import { useState, useRef } from "react";
import { INSTRUCTOR_SPOTLIGHT } from "@/lib/data";
import { fadeUp, staggerContainer, viewportOnce } from "@/lib/motion";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";

export default function InstructorSpotlight() {
  const [slide, setSlide] = useState(0);
  const containerRef = useRef(null);
  
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"]
  });

  // Parallax values for floating elements
  const y1 = useTransform(scrollYProgress, [0, 1], [150, -150]);
  const y2 = useTransform(scrollYProgress, [0, 1], [-100, 100]);
  const y3 = useTransform(scrollYProgress, [0, 1], [200, -200]);

  const slides = [
    "AI dev environment with checkpoint overlays active",
    "Curriculum map showing segmented concept nodes",
  ];

  return (
    <section
      id="instructor-spotlight"
      className="bg-canvas px-6 py-16 md:py-32 scroll-mt-24 relative overflow-hidden"
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
          className="font-mono text-sm tracking-widest text-indigo-600 font-semibold uppercase"
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

        <div className="relative mt-12 md:mt-16" ref={containerRef}>
          {/* Parallax Floating Elements */}
          <motion.div 
            style={{ y: y1 }}
            className="absolute -right-6 top-1/4 z-30 hidden lg:flex flex-col gap-2 rounded-2xl bg-white/90 backdrop-blur p-4 shadow-2xl border border-ink/5 w-[220px]"
          >
             <div className="flex items-center gap-2 text-xs font-mono font-bold text-indigo-600">
               <Cpu className="w-4 h-4" /> AI Checkpoint
             </div>
             <p className="text-xs text-ink-soft leading-relaxed">Analyzing syntax tree for conceptual gaps...</p>
             <div className="h-1.5 w-full bg-ink/5 rounded-full overflow-hidden mt-1">
               <motion.div className="h-full bg-indigo-500" animate={{ width: ["0%", "100%", "0%"] }} transition={{ duration: 4, repeat: Infinity, ease: "linear" }} />
             </div>
          </motion.div>

          <motion.div 
            style={{ y: y2 }}
            className="absolute -left-12 bottom-1/3 z-30 hidden lg:block rounded-2xl bg-zinc-950 p-5 shadow-2xl border border-white/10"
          >
             <div className="flex items-center gap-2 mb-3">
               <Code2 className="w-4 h-4 text-lime" />
               <span className="text-xs font-mono text-zinc-400">sandbox.py</span>
             </div>
             <pre className="text-[11px] font-mono leading-loose">
               <span className="text-pink-400">def</span> <span className="text-blue-400">verify_mastery</span><span className="text-zinc-300">(user):</span>{'\n'}
               <span className="text-lime">  return</span> <span className="text-zinc-300">score *</span> <span className="text-orange-400">1.5</span>
             </pre>
          </motion.div>

          <motion.div
            variants={fadeUp}
            custom={2}
            className="relative h-[360px] overflow-hidden rounded-2xl bg-zinc-950 md:h-[540px] shadow-[0_20px_50px_rgba(0,0,0,0.3)] border border-white/10"
          >
            {/* Video 1 (Overview) */}
            <iframe
              src={`https://www.youtube.com/embed/M5QY2_8704o?autoplay=1&mute=1&loop=1&controls=0&showinfo=0&playlist=M5QY2_8704o&modestbranding=1`}
              className={`absolute top-1/2 left-1/2 w-[150%] h-[150%] -translate-x-1/2 -translate-y-1/2 object-cover transition-opacity duration-700 pointer-events-none ${slide === 0 ? "opacity-100 z-0" : "opacity-0 -z-10"}`}
              allow="autoplay; encrypted-media"
              frameBorder="0"
            />
            {/* Video 2 (Curriculum Map) */}
            <iframe
              src={`https://www.youtube.com/embed/M5QY2_8704o?autoplay=1&mute=1&loop=1&controls=0&showinfo=0&start=600&playlist=M5QY2_8704o&modestbranding=1`}
              className={`absolute top-1/2 left-1/2 w-[150%] h-[150%] -translate-x-1/2 -translate-y-1/2 object-cover transition-opacity duration-700 pointer-events-none ${slide === 1 ? "opacity-100 z-0" : "opacity-0 -z-10"}`}
              allow="autoplay; encrypted-media"
              frameBorder="0"
            />
            
            <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/20 to-transparent z-10 pointer-events-none" aria-hidden="true" />
            
            <div className="absolute inset-0 flex items-end justify-center pb-28 md:pb-32 z-10 pointer-events-none">
              <p className="max-w-md px-6 text-center text-sm text-white font-medium md:text-base drop-shadow-2xl">
                {slides[slide]}
              </p>
            </div>

            <div className="absolute left-4 top-4 md:left-6 md:top-6 z-20">
              <Tabs value={slide === 0 ? "overview" : "curriculum"} onValueChange={(val) => setSlide(val === "overview" ? 0 : 1)}>
                <TabsList className="border border-white/10 bg-black/40 backdrop-blur-xl">
                  <TabsTrigger value="overview" className="data-[state=active]:bg-white/20 data-[state=active]:text-white text-zinc-400">Overview</TabsTrigger>
                  <TabsTrigger value="curriculum" className="data-[state=active]:bg-white/20 data-[state=active]:text-white text-zinc-400">Curriculum Map</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>

            <div className="absolute bottom-4 left-4 right-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between md:bottom-8 md:left-8 md:right-8 z-20">
              <Button className="w-fit rounded-full bg-white text-ink hover:bg-white/90 shadow-xl border border-white/20 font-bold px-6 h-12">
                <span className="mr-3 flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-white shadow-inner">
                  <Play className="h-4 w-4 fill-white translate-x-0.5" />
                </span>
                {INSTRUCTOR_SPOTLIGHT.cta}
              </Button>

              <div className="flex gap-3 self-end sm:self-auto">
                <motion.button
                  type="button"
                  onClick={() => setSlide((s) => (s === 0 ? 1 : 0))}
                  className="flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-black/40 backdrop-blur-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 shadow-lg"
                  whileHover={{ scale: 1.1, backgroundColor: "rgba(255,255,255,0.2)" }}
                  whileTap={{ scale: 0.95 }}
                  aria-label="Previous slide"
                >
                  <ChevronLeft className="h-6 w-6 text-white" />
                </motion.button>
                <motion.button
                  type="button"
                  onClick={() => setSlide((s) => (s === 0 ? 1 : 0))}
                  className="flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-black/40 backdrop-blur-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 shadow-lg"
                  whileHover={{ scale: 1.1, backgroundColor: "rgba(255,255,255,0.2)" }}
                  whileTap={{ scale: 0.95 }}
                  aria-label="Next slide"
                >
                  <ChevronRight className="h-6 w-6 text-white" />
                </motion.button>
              </div>
            </div>
          </motion.div>
        </div>
      </motion.div>
    </section>
  );
}
