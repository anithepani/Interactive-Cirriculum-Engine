"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { EXERCISE_TYPES, VALUE_PROPOSITION_COPY } from "@/lib/data";
import { fadeUp, viewportOnce } from "@/lib/motion";

export default function ValuePropositionFan() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });

  const rotate0 = useTransform(scrollYProgress, [0.2, 0.55], [0, EXERCISE_TYPES[0].rotate]);
  const rotate1 = useTransform(scrollYProgress, [0.2, 0.55], [0, EXERCISE_TYPES[1].rotate]);
  const rotate2 = useTransform(scrollYProgress, [0.2, 0.55], [0, EXERCISE_TYPES[2].rotate]);
  const y0 = useTransform(scrollYProgress, [0.2, 0.55], [40, EXERCISE_TYPES[0].yOffset]);
  const y1 = useTransform(scrollYProgress, [0.2, 0.55], [40, EXERCISE_TYPES[1].yOffset]);
  const y2 = useTransform(scrollYProgress, [0.2, 0.55], [40, EXERCISE_TYPES[2].yOffset]);
  const transforms = [
    { rotate: rotate0, y: y0 },
    { rotate: rotate1, y: y1 },
    { rotate: rotate2, y: y2 },
  ];

  return (
    <section ref={ref} id="features" className="bg-canvas px-6 py-16 md:py-24">
      <div className="mx-auto grid max-w-container gap-12 md:grid-cols-2 md:items-center">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          variants={fadeUp}
        >
          <p className="font-display text-3xl font-medium leading-snug text-ink md:text-4xl">
            {VALUE_PROPOSITION_COPY}
          </p>
        </motion.div>

        <div className="relative mx-auto h-80 w-full max-w-sm md:mx-0 md:max-w-none">
          {EXERCISE_TYPES.map((exercise, i) => (
            <motion.div
              key={exercise.key}
              style={{
                rotate: transforms[i].rotate,
                y: transforms[i].y,
                zIndex: i,
              }}
              className={`absolute left-1/2 top-1/2 flex h-64 w-52 -translate-x-1/2 -translate-y-1/2 flex-col justify-between rounded-xl2 p-6 text-white shadow-xl ${exercise.bgClass}`}
            >
              <h3 className="font-display text-xl font-bold">{exercise.title}</h3>
              <p className="text-sm text-white/85">{exercise.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
