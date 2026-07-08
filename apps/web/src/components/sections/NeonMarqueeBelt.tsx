"use client";

import { NEON_MARQUEE_TEXT } from "@/lib/data";

const SHAPES = ["○", "△", "□", "◇", "○", "△"];

export default function NeonMarqueeBelt() {
  const textTrack = Array(4).fill(NEON_MARQUEE_TEXT).join("");
  const shapeTrack = [...SHAPES, ...SHAPES, ...SHAPES, ...SHAPES];

  return (
    <section className="relative overflow-hidden py-8 md:py-12" aria-label="Brand marquee">
      <div className="relative left-1/2 w-screen -translate-x-1/2 -rotate-1 bg-lime py-6 md:py-8">
        <div className="overflow-hidden">
          <div className="flex w-max motion-safe:animate-marquee">
            <p className="whitespace-nowrap px-4 font-display text-2xl font-black uppercase text-ink md:text-6xl">
              {textTrack}
            </p>
            <p className="whitespace-nowrap px-4 font-display text-2xl font-black uppercase text-ink md:text-6xl" aria-hidden="true">
              {textTrack}
            </p>
          </div>
        </div>

        <div className="pointer-events-none absolute inset-0 overflow-hidden opacity-30">
          <div className="flex w-max motion-safe:animate-marqueeReverse gap-12 pt-2 text-2xl text-ink md:text-4xl">
            {[...shapeTrack, ...shapeTrack].map((shape, i) => (
              <span key={i} aria-hidden="true">
                {shape}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
