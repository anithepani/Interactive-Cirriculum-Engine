"use client";

import { motion, useMotionValue, useSpring, useTransform, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { LEARNER_MATRIX_COPY } from "@/lib/data";
import { fadeUp, viewportOnce } from "@/lib/motion";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { BadgeCheck, Flame, Code2 } from "lucide-react";

// The constellation nodes
const NODES = [
  { id: 0, x: 20, y: 30, initials: "SA", name: "Sarah A.", mastery: "92%", streak: 14, recent: "React Hooks" },
  { id: 1, x: 50, y: 20, initials: "DE", name: "David E.", mastery: "88%", streak: 5, recent: "Redux Toolkit" },
  { id: 2, x: 80, y: 40, initials: "MA", name: "Mike A.", mastery: "95%", streak: 21, recent: "Next.js Routing" },
  { id: 3, x: 30, y: 60, initials: "PR", name: "Priya R.", mastery: "78%", streak: 3, recent: "Tailwind CSS" },
  { id: 4, x: 60, y: 70, initials: "TR", name: "Tom R.", mastery: "84%", streak: 8, recent: "Python Basics" },
  { id: 5, x: 10, y: 80, initials: "AR", name: "Alex R.", mastery: "99%", streak: 45, recent: "Advanced Recursion" },
  { id: 6, x: 90, y: 80, initials: "ZU", name: "Zoe U.", mastery: "91%", streak: 12, recent: "Docker Setup" },
];

// Which nodes are connected? (indices)
const EDGES = [
  [0, 1], [1, 2], [0, 3], [1, 4], [3, 4], [2, 4], [3, 5], [4, 6], [2, 6]
];

export default function LearnerMatrix() {
  const [finePointer, setFinePointer] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);
  
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 80, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 80, damping: 20 });
  const parallaxX = useTransform(springX, [-0.5, 0.5], [-15, 15]);
  const parallaxY = useTransform(springY, [-0.5, 0.5], [-10, 10]);

  useEffect(() => {
    setFinePointer(window.matchMedia("(pointer: fine)").matches);
  }, []);

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
        >
          <h2 className="relative z-10 font-display text-4xl font-bold text-ink md:text-5xl">
            {LEARNER_MATRIX_COPY.headline}
          </h2>
          <p className="relative z-10 mx-auto mt-4 max-w-xl text-ink-soft">
            {LEARNER_MATRIX_COPY.subcaption}
          </p>
        </motion.div>

        <motion.div
          className="relative mx-auto mt-12 h-[500px] max-w-5xl"
          style={finePointer ? { x: parallaxX, y: parallaxY } : undefined}
        >
          {/* SVG Connections */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
            {EDGES.map(([startIdx, endIdx], i) => {
              const start = NODES[startIdx];
              const end = NODES[endIdx];
              const isHovered = hoveredNode === startIdx || hoveredNode === endIdx;
              const isAnyHovered = hoveredNode !== null;
              
              return (
                <motion.line
                  key={`edge-${i}`}
                  x1={`${start.x}%`}
                  y1={`${start.y}%`}
                  x2={`${end.x}%`}
                  y2={`${end.y}%`}
                  stroke={isHovered ? "var(--accent-blue)" : "var(--ink)"}
                  strokeWidth={isHovered ? 2 : 1}
                  className="transition-colors duration-500"
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: isHovered ? 0.6 : isAnyHovered ? 0.05 : 0.15 }}
                  transition={{ duration: 0.5 }}
                />
              );
            })}
          </svg>

          {/* Nodes */}
          {NODES.map((node) => (
            <div
              key={node.id}
              className="absolute group z-10"
              style={{ left: `${node.x}%`, top: `${node.y}%`, transform: 'translate(-50%, -50%)' }}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
            >
              {/* Avatar Node */}
              <motion.div 
                className={`relative w-12 h-12 rounded-full border-2 cursor-pointer shadow-lg transition-all duration-300 flex items-center justify-center bg-white ${hoveredNode === node.id ? 'border-blue scale-110 shadow-blue/20' : hoveredNode !== null ? 'border-transparent opacity-40' : 'border-ink/10 hover:border-blue'}`}
                whileHover={{ scale: 1.15 }}
              >
                <span className="font-mono text-sm font-semibold text-ink">{node.initials}</span>
                
                {/* Ping animation when hovered */}
                {hoveredNode === node.id && (
                  <span className="absolute inset-0 rounded-full bg-blue/30 animate-ping" />
                )}
              </motion.div>

              {/* Data Card Popover */}
              <AnimatePresence>
                {hoveredNode === node.id && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 5, scale: 0.95 }}
                    className="absolute left-1/2 -translate-x-1/2 top-full mt-4 w-48 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-md rounded-xl p-3 shadow-2xl border border-ink/10 pointer-events-none"
                    style={{ zIndex: 50 }}
                  >
                    <div className="flex items-center justify-between mb-2 pb-2 border-b border-ink/10">
                      <span className="font-bold text-sm text-ink">{node.name}</span>
                      <span className="flex items-center text-xs font-semibold text-lime-600 dark:text-lime-400 bg-lime-500/10 px-1.5 py-0.5 rounded">
                        <BadgeCheck className="w-3 h-3 mr-1" /> {node.mastery}
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex items-center text-xs text-ink-soft">
                        <Flame className="w-3.5 h-3.5 mr-1.5 text-orange-500" /> {node.streak} Day Streak
                      </div>
                      <div className="flex items-center text-xs text-ink-soft">
                        <Code2 className="w-3.5 h-3.5 mr-1.5 text-blue-500" /> {node.recent}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
