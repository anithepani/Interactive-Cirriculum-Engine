"use client";

import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { CURRICULUM_ITEMS, MARKETPLACE_COPY } from "@/lib/data";
import { fadeUp, viewportOnce } from "@/lib/motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function MarketplaceCarousel() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  const updateIndex = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const cardWidth = el.firstElementChild?.clientWidth ?? 1;
    const gap = 24;
    setActiveIndex(Math.round(el.scrollLeft / (cardWidth + gap)));
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.addEventListener("scroll", updateIndex, { passive: true });
    return () => el.removeEventListener("scroll", updateIndex);
  }, [updateIndex]);

  const scrollBy = (dir: -1 | 1) => {
    const el = scrollRef.current;
    if (!el) return;
    const cardWidth = el.firstElementChild?.clientWidth ?? 320;
    el.scrollBy({ left: dir * (cardWidth + 24), behavior: "smooth" });
  };

  return (
    <section id="marketplace" className="bg-canvas px-6 py-16 md:py-24">
      <motion.div
        className="mx-auto max-w-container"
        initial="hidden"
        whileInView="visible"
        viewport={viewportOnce}
        variants={fadeUp}
      >
        <Badge variant="lime" className="mb-4 px-3 py-1 uppercase tracking-wider">
          {MARKETPLACE_COPY.badge}
        </Badge>
        <h2 className="font-display text-4xl font-bold text-ink">{MARKETPLACE_COPY.headline}</h2>
        <p className="mt-4 max-w-2xl text-ink-soft">{MARKETPLACE_COPY.body}</p>
        <Button variant="hotpink" className="mt-6 rounded-full">
          {MARKETPLACE_COPY.cta}
        </Button>

        <div className="relative mt-10">
          <div
            ref={scrollRef}
            className="scrollbar-hide flex snap-x snap-mandatory gap-6 overflow-x-auto pb-4"
          >
            {CURRICULUM_ITEMS.map((item) => (
              <article
                key={item.id}
                className="w-[280px] shrink-0 snap-start rounded-xl2 border border-ink/10 bg-white p-5 shadow-card sm:w-[320px]"
              >
                <div className={`h-36 rounded-xl ${item.accent} opacity-80`} />
                <h3 className="mt-4 font-display text-lg font-bold">{item.title}</h3>
                <p className="mt-1 font-mono text-xs text-ink-soft">{item.lessons} lessons</p>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-ink/10">
                  <motion.div
                    className={`h-full rounded-full ${item.accent}`}
                    initial={{ width: 0 }}
                    whileInView={{ width: `${item.progress}%` }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                  />
                </div>
              </article>
            ))}
          </div>

          <div className="mt-6 flex items-center justify-between">
            <div className="flex gap-2">
              {CURRICULUM_ITEMS.map((_, i) => (
                <div
                  key={i}
                  className={`h-1 rounded-full transition-all ${i === activeIndex ? "w-8 bg-ink" : "w-4 bg-ink/20"}`}
                />
              ))}
            </div>
            <div className="flex gap-2">
              <motion.button
                type="button"
                onClick={() => scrollBy(-1)}
                className="flex h-12 w-12 items-center justify-center rounded-full border border-ink/15 bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                aria-label="Scroll carousel left"
              >
                <ChevronLeft className="h-5 w-5" />
              </motion.button>
              <motion.button
                type="button"
                onClick={() => scrollBy(1)}
                className="flex h-12 w-12 items-center justify-center rounded-full border border-ink/15 bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                aria-label="Scroll carousel right"
              >
                <ChevronRight className="h-5 w-5" />
              </motion.button>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
