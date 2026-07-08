"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, useState } from "react";
import {
  LEARNER_CHIPS_DESKTOP,
  LEARNER_CHIPS_MOBILE,
  LEARNER_MATRIX_COPY,
} from "@/lib/data";
import { fadeUp, viewportOnce } from "@/lib/motion";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

export default function LearnerMatrix() {
  const [finePointer, setFinePointer] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 80, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 80, damping: 20 });
  const parallaxX = useTransform(springX, [-0.5, 0.5], [-12, 12]);
  const parallaxY = useTransform(springY, [-0.5, 0.5], [-8, 8]);

  useEffect(() => {
    setFinePointer(window.matchMedia("(pointer: fine)").matches);
    const mobileMq = window.matchMedia("(max-width: 639px)");
    const setMobile = () => setIsMobile(mobileMq.matches);
    setMobile();
    mobileMq.addEventListener("change", setMobile);
    return () => mobileMq.removeEventListener("change", setMobile);
  }, []);

  const chips = isMobile ? LEARNER_CHIPS_MOBILE : LEARNER_CHIPS_DESKTOP;

  return (
    <section
      className="relative overflow-hidden bg-canvas px-6 py-20 md:py-28"
      onMouseMove={
        finePointer
          ? (e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              mouseX.set((e.clientX - rect.left) / rect.width - 0.5);
              mouseY.set((e.clientY - rect.top) / rect.height - 0.5);
            }
          : undefined
      }
    >
      <div className="mx-auto max-w-container text-center">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          variants={fadeUp}
          custom={0}
        >
          <h2 className="relative z-10 font-display text-4xl font-bold text-ink md:text-5xl">
            {LEARNER_MATRIX_COPY.headline}
          </h2>
          <p className="relative z-10 mx-auto mt-4 max-w-xl text-ink-soft">
            {LEARNER_MATRIX_COPY.subcaption}
          </p>
        </motion.div>

        <motion.div
          className="relative mx-auto mt-12 h-[420px] max-w-4xl md:h-[480px]"
          style={finePointer ? { x: parallaxX, y: parallaxY } : undefined}
        >
          {chips.map((chip) =>
            chip.type === "avatar" ? (
              <Avatar
                key={chip.id}
                className="absolute border-2 border-white shadow-md"
                style={{
                  left: `${chip.x}%`,
                  top: `${chip.y}%`,
                  width: chip.size,
                  height: chip.size,
                }}
              >
                <AvatarFallback>{chip.label.slice(0, 2).toUpperCase()}</AvatarFallback>
              </Avatar>
            ) : (
              <Badge
                key={chip.id}
                variant="lime"
                className="absolute px-3 py-1.5 text-xs"
                style={{ left: `${chip.x}%`, top: `${chip.y}%` }}
              >
                {chip.label}
              </Badge>
            )
          )}
        </motion.div>
      </div>
    </section>
  );
}
