"use client";

import { motion } from "framer-motion";
import { Play, Youtube, BrainCircuit } from "lucide-react";
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
        <div className="relative mb-6 h-56 w-full overflow-hidden rounded-xl bg-zinc-950 p-5 shadow-inner">
           {/* Fake terminal header */}
           <div className="flex gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <div className="w-3 h-3 rounded-full bg-green-500/80" />
           </div>
           {/* Fake terminal code */}
           <div className="font-mono text-xs sm:text-sm leading-loose">
             <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} transition={{ delay: 0.2 }} className="text-blue-400 font-semibold">> ICE INGESTION_WORKER --url "youtube.com/..."</motion.p>
             <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} transition={{ delay: 0.8 }} className="text-zinc-400 mt-2">[✓] Transcript fetched (12,400 tokens)</motion.p>
             <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} transition={{ delay: 1.4 }} className="text-zinc-400">[✓] Concepts segmented (7 blocks)</motion.p>
             <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} transition={{ delay: 2.0 }} className="text-lime mt-2">> Generating Checkpoints...</motion.p>
             <motion.div 
                className="mt-3 h-1.5 bg-white/10 rounded-full overflow-hidden"
                initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} transition={{ delay: 2.0 }}
             >
                <motion.div className="h-full bg-lime" initial={{ width: "0%" }} whileInView={{ width: "100%" }} transition={{ delay: 2.0, duration: 2, ease: "linear", repeat: Infinity }} />
             </motion.div>
           </div>
        </div>
        {card.badge && (
          <Badge className="absolute right-4 top-4 bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg border-none">{card.badge}</Badge>
        )}
      </>
    );
  }
  if (card.variant === "blue") {
    return (
      <div className="relative h-48 mb-4 overflow-hidden rounded-xl border border-white/10 bg-blue/80 flex items-center justify-center">
         {/* Network of logic mapping */}
         <svg className="absolute inset-0 w-full h-full opacity-50" aria-hidden="true">
            <motion.path d="M -50 80 Q 150 -20 350 80" stroke="rgba(255,255,255,0.4)" strokeWidth="2" fill="none" strokeDasharray="5 5" animate={{ strokeDashoffset: [0, -100] }} transition={{ duration: 4, repeat: Infinity, ease: "linear" }} />
            <motion.path d="M -50 80 Q 150 180 350 80" stroke="rgba(255,255,255,0.4)" strokeWidth="2" fill="none" strokeDasharray="5 5" animate={{ strokeDashoffset: [0, -100] }} transition={{ duration: 4, repeat: Infinity, ease: "linear" }} />
         </svg>
         
         <div className="flex items-center gap-4 sm:gap-8 relative z-10">
            <motion.div whileHover={{ scale: 1.1, rotate: -10 }} className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-md shadow-lg border border-white/30 flex items-center justify-center">
               <Youtube className="w-7 h-7 text-white" />
            </motion.div>
            <motion.div className="w-12 sm:w-16 h-1.5 rounded-full bg-gradient-to-r from-transparent via-white to-transparent" animate={{ opacity: [0.2, 1, 0.2] }} transition={{ duration: 2, repeat: Infinity }} />
            <motion.div whileHover={{ scale: 1.1, rotate: 10 }} className="w-14 h-14 rounded-2xl bg-white shadow-xl flex items-center justify-center">
               <BrainCircuit className="w-7 h-7 text-blue" />
            </motion.div>
         </div>
      </div>
    );
  }
  if (card.variant === "photo") {
    return (
      <div className="relative h-48 mb-4 rounded-xl bg-zinc-950 p-4 border border-ink/10 shadow-inner flex flex-col font-mono text-xs sm:text-sm">
         <div className="flex justify-between items-center mb-3 border-b border-white/10 pb-3">
            <div className="flex gap-4">
               <span className="text-zinc-500">main.py</span>
               <span className="text-indigo-400 border-b border-indigo-400">test.py</span>
            </div>
            {card.telemetry && (
               <div className="flex gap-2 hidden sm:flex">
                 {card.telemetry.map((t) => (
                   <Badge key={t} variant="secondary" className="bg-white/10 text-white/80 hover:bg-white/20">{t}</Badge>
                 ))}
               </div>
            )}
         </div>
         <p className="text-purple-400">def <span className="text-blue-400">fibonacci</span>(n):</p>
         <p className="pl-4 text-zinc-500"># Generated practice overlay</p>
         <p className="pl-4 text-pink-400">if <span className="text-zinc-300">n &lt;= 1:</span></p>
         <p className="pl-8 text-lime">return <span className="text-zinc-300">n</span></p>
         <p className="pl-4 text-lime">return <span className="text-blue-400">fibonacci</span><span className="text-zinc-300">(n-1) + </span><span className="text-blue-400">fibonacci</span><span className="text-zinc-300">(n-2)</span></p>
         
         <motion.div 
            className="absolute bottom-4 right-4 bg-lime/10 text-lime border border-lime/30 px-3 py-1.5 rounded-md shadow-[0_0_15px_rgba(198,255,61,0.1)] font-bold text-xs"
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
         >
            Tests Passed!
         </motion.div>
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
