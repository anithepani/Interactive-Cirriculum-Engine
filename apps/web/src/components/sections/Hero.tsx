"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { HERO_COPY } from "@/lib/data";
import { cardFanSpring, staggerContainer } from "@/lib/motion";
import { useTypewriterCycle } from "@/lib/hooks/useTypewriterCycle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const CARD_BG: Record<string, string> = {
  lime: "bg-lime",
  coral: "bg-coral",
  hotpink: "bg-hotpink",
  blue: "bg-blue",
  orange: "bg-orange",
};

const DESKTOP_FAN = [-12, -6, 0, 6, 12];
const MOBILE_FAN = [-6, 0, 6];
const TAG_STYLES = [
  "bg-lime text-ink",
  "bg-blue text-white",
  "bg-hotpink text-white",
];

const cardVariants = {
  hidden: { x: 0, rotate: 0, opacity: 0.6 },
  visible: (fanRotate: number) => ({
    x: fanRotate * 3,
    rotate: fanRotate,
    opacity: 1,
    transition: cardFanSpring,
  }),
};

export default function Hero() {
  const { displayText, opacity } = useTypewriterCycle(HERO_COPY.typewriter);

  const scrollToDemo = () => {
    document.getElementById("instructor-spotlight")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center bg-canvas px-6 pb-20 pt-28">
      <motion.h1
        className="max-w-5xl text-center font-display text-4xl font-black leading-[0.95] text-ink sm:text-6xl md:text-8xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <span style={{ opacity }}>{displayText}</span>
        <span className="animate-pulse">|</span>
      </motion.h1>

      <div className="relative mx-auto mt-16 h-72 w-full max-w-2xl md:mt-20 md:h-80">
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {/* Desktop: 5 cards */}
          <div className="hidden md:block">
            {HERO_COPY.cardColors.map((color, i) => (
              <motion.div
                key={color}
                custom={DESKTOP_FAN[i]}
                variants={cardVariants}
                className={cn(
                  "absolute left-1/2 top-1/2 h-72 w-56 -translate-x-1/2 -translate-y-1/2 rounded-xl2 shadow-2xl",
                  CARD_BG[color]
                )}
                style={{ zIndex: i }}
              />
            ))}
          </div>
          {/* Mobile: 3 cards */}
          <div className="md:hidden">
            {HERO_COPY.cardColors.slice(0, 3).map((color, i) => (
              <motion.div
                key={`m-${color}`}
                custom={MOBILE_FAN[i]}
                variants={cardVariants}
                className={cn(
                  "absolute left-1/2 top-1/2 h-40 w-28 -translate-x-1/2 -translate-y-1/2 rounded-xl2 shadow-2xl",
                  CARD_BG[color]
                )}
                style={{ zIndex: i }}
              />
            ))}
          </div>
        </motion.div>

        {HERO_COPY.floatingTags.map((tag, i) => (
          <span
            key={tag}
            className={cn(
              "absolute animate-floatY rounded-full px-3 py-1 font-mono text-xs font-semibold",
              TAG_STYLES[i],
              i === 0 && "left-0 top-4",
              i === 1 && "right-0 top-12",
              i === 2 && "bottom-8 left-1/4"
            )}
            style={{ animationDelay: `${i * 0.7}s` }}
          >
            {tag}
          </span>
        ))}
      </div>

      <motion.div
        className="mt-10 flex flex-col items-center gap-4 sm:flex-row"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.5 }}
      >
        <motion.div whileHover={{ scale: 1.03 }}>
          <Button asChild size="lg" className="rounded-full bg-ink px-8 py-4 text-base text-white">
            <Link href="/upload">{HERO_COPY.primaryCta}</Link>
          </Button>
        </motion.div>
        <button
          type="button"
          onClick={scrollToDemo}
          className="group inline-flex items-center gap-2 font-semibold text-ink transition hover:text-ink/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30 focus-visible:rounded-lg"
        >
          {HERO_COPY.secondaryCta}
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
        </button>
      </motion.div>
    </section>
  );
}
