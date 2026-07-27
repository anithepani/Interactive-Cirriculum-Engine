"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { DUAL_CTA } from "@/lib/data";
import { fadeUp, staggerContainer, viewportOnce } from "@/lib/motion";
import { Button } from "@/components/ui/button";

function OrganicShapes() {
  return (
    <svg
      className="absolute inset-0 h-full w-full opacity-30"
      viewBox="0 0 400 420"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <motion.circle
        cx="320"
        cy="80"
        r="120"
        fill="#C6FF3D"
        animate={{ cx: [320, 300, 320], cy: [80, 100, 80] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.ellipse
        cx="80"
        cy="300"
        rx="90"
        ry="60"
        fill="#3D6BFF"
        animate={{ rx: [90, 110, 90] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.path
        d="M200,200 Q280,120 360,220 T200,360"
        fill="none"
        stroke="#FF3D8C"
        strokeWidth="3"
        animate={{ d: ["M200,200 Q280,120 360,220 T200,360", "M200,220 Q260,140 340,240 T180,340", "M200,200 Q280,120 360,220 T200,360"] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />
    </svg>
  );
}

export default function DualCTABlocks() {
  return (
    <section className="bg-canvas px-6 py-16 md:py-24">
      <motion.div
        className="mx-auto grid max-w-container gap-6 md:grid-cols-2"
        initial="hidden"
        whileInView="visible"
        viewport={viewportOnce}
        variants={staggerContainer}
      >
        {DUAL_CTA.map((block, i) => (
          <motion.article
            key={block.key}
            variants={fadeUp}
            custom={i}
            whileHover={{ scale: 1.01 }}
            className={`relative flex h-[320px] flex-col justify-end overflow-hidden rounded-xl2 p-10 text-white md:h-[420px] ${block.bgClass}`}
          >
            {block.key === "peers" && (
              <div
                className="absolute inset-0 bg-gradient-to-t from-surfaceBurgundy via-surfaceBurgundy/80 to-transparent opacity-40"
                aria-hidden="true"
              />
            )}
            {block.key === "archive" && <OrganicShapes />}

            <div className="relative z-10">
              <h2 className="font-display text-3xl font-bold md:text-4xl">{block.title}</h2>
              <p className="mt-2 max-w-sm text-white/80">{block.subtitle}</p>
              <Button
                asChild
                className={`mt-6 rounded-full font-semibold ${block.buttonClass}`}
              >
                <Link href="/signup">{block.cta}</Link>
              </Button>
            </div>
          </motion.article>
        ))}
      </motion.div>
    </section>
  );
}
