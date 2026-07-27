"use client";

import Link from "next/link";
import Image from "next/image";
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
      <div className="flex flex-col justify-end min-h-[120px] sm:min-h-[150px] md:min-h-[200px]">
        <motion.h1
          className="max-w-5xl text-center font-display text-4xl font-black leading-[0.95] text-ink sm:text-6xl md:text-8xl"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span style={{ opacity }}>{displayText}</span>
          <span className="animate-pulse">|</span>
        </motion.h1>
      </div>

      <div className="relative mx-auto mt-16 h-72 w-full max-w-5xl overflow-hidden group">
        <div className="flex gap-6 w-max animate-marquee group-hover:[animation-play-state:paused]">
          {[...HERO_COPY.cardColors, ...HERO_COPY.cardColors].map((color, i) => (
            <div
              key={`${color}-${i}`}
              className="h-72 w-56 rounded-xl2 shadow-xl overflow-hidden border-2 border-white/10 relative shrink-0 group/card cursor-pointer"
            >
              <div className="absolute inset-0 transition-transform duration-[10s] ease-in-out group-hover/card:scale-110 scale-105">
                <Image src={`/images/story/${(i % 5) + 1}.jpg`} alt={`Story ${(i % 5) + 1}`} fill className="object-cover" />
              </div>
            </div>
          ))}
        </div>

        {HERO_COPY.floatingTags.map((tag, i) => (
          <span
            key={tag}
            className={cn(
              "absolute animate-floatY rounded-full px-3 py-1 font-mono text-xs font-semibold z-10",
              TAG_STYLES[i],
              i === 0 && "left-4 top-4",
              i === 1 && "right-4 top-12",
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
