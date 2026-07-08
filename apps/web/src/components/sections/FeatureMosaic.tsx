"use client";

import { motion } from "framer-motion";
import { Play } from "lucide-react";
import { FEATURE_CARDS } from "@/lib/data";
import { fadeUp, staggerContainer, viewportOnce } from "@/lib/motion";
import { Badge } from "@/components/ui/badge";

function NodeGraph() {
  const nodes = [
    { cx: 50, cy: 30 },
    { cx: 25, cy: 60 },
    { cx: 75, cy: 60 },
    { cx: 50, cy: 85 },
  ];
  return (
    <svg viewBox="0 0 100 100" className="h-32 w-full" aria-hidden="true">
      <line x1="50" y1="30" x2="25" y2="60" stroke="rgba(198,255,61,0.5)" strokeWidth="1" />
      <line x1="50" y1="30" x2="75" y2="60" stroke="rgba(198,255,61,0.5)" strokeWidth="1" />
      <line x1="25" y1="60" x2="50" y2="85" stroke="rgba(198,255,61,0.5)" strokeWidth="1" />
      <line x1="75" y1="60" x2="50" y2="85" stroke="rgba(198,255,61,0.5)" strokeWidth="1" />
      {nodes.map((n, i) => (
        <circle key={i} cx={n.cx} cy={n.cy} r="6" fill="#C6FF3D" />
      ))}
    </svg>
  );
}

function FeatureCardContent({ card }: { card: (typeof FEATURE_CARDS)[0] }) {
  if (card.variant === "light") {
    return (
      <>
        <div className="relative mb-4 flex gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 flex-1 rounded-lg bg-ink/5" />
          ))}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-ink text-white shadow-lg">
              <Play className="h-5 w-5 fill-white" />
            </div>
          </div>
        </div>
        {card.badge && (
          <Badge className="absolute right-4 top-4 bg-blue text-white">{card.badge}</Badge>
        )}
      </>
    );
  }
  if (card.variant === "blue") {
    return (
      <div className="relative h-32 overflow-hidden rounded-xl">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="absolute rounded-full bg-white/20"
            style={{ width: 80 + i * 40, height: 80 + i * 40, left: `${20 + i * 15}%`, top: `${10 + i * 10}%` }}
            animate={{ rotate: 360 }}
            transition={{ duration: 20 + i * 5, repeat: Infinity, ease: "linear" }}
          />
        ))}
      </div>
    );
  }
  if (card.variant === "photo") {
    return (
      <div className="relative h-32 rounded-xl bg-gradient-to-br from-hotpink/30 via-orange/30 to-lime/30">
        {card.telemetry?.map((t, i) => (
          <Badge key={t} variant="outline" className="absolute bg-white/90" style={{ top: 8 + i * 32, left: 8 }}>
            {t}
          </Badge>
        ))}
      </div>
    );
  }
  return <NodeGraph />;
}

export default function FeatureMosaic() {
  const cardStyles: Record<string, string> = {
    light: "bg-white border border-ink/10",
    blue: "bg-blue text-white",
    photo: "bg-white border border-ink/10",
    dark: "border border-white/10 bg-surfaceDark/90 text-white backdrop-blur",
  };

  return (
    <section className="bg-canvas px-6 py-16 md:py-24">
      <motion.div
        className="mx-auto max-w-container"
        initial="hidden"
        whileInView="visible"
        viewport={viewportOnce}
        variants={staggerContainer}
      >
        <motion.h2 variants={fadeUp} custom={0} className="mb-10 text-center font-display text-3xl font-bold text-ink md:text-4xl">
          Every Art Piece Sells a Story
        </motion.h2>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {FEATURE_CARDS.map((card, i) => (
            <motion.article
              key={card.key}
              variants={fadeUp}
              custom={i + 1}
              whileHover={{ y: -6, boxShadow: "0 24px 40px rgba(0,0,0,0.12)" }}
              className={`relative rounded-xl2 p-6 shadow-card ${cardStyles[card.variant]} ${i === 0 ? "md:row-span-2" : ""}`}
            >
              <FeatureCardContent card={card} />
              <h3 className="mt-4 font-display text-xl font-bold">{card.title}</h3>
              <p className={`mt-2 text-sm ${card.variant === "dark" || card.variant === "blue" ? "text-white/80" : "text-ink-soft"}`}>
                {card.description}
              </p>
            </motion.article>
          ))}
        </div>
      </motion.div>
    </section>
  );
}
