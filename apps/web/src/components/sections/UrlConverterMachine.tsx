"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, CheckCircle2, Youtube, Sparkles, Code2, BrainCircuit } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function UrlConverterMachine() {
  const [status, setStatus] = useState<"idle" | "processing" | "complete">("idle");
  const [stepIndex, setStepIndex] = useState(0);

  const steps = [
    { icon: Youtube, text: "Fetching Video & Transcript..." },
    { icon: BrainCircuit, text: "AI Segmenting Concepts..." },
    { icon: Sparkles, text: "Generating MCQ Checkpoints..." },
    { icon: Code2, text: "Scaffolding Sandbox Labs..." },
  ];

  useEffect(() => {
    if (status === "processing") {
      const interval = setInterval(() => {
        setStepIndex((prev) => {
          if (prev >= steps.length - 1) {
            clearInterval(interval);
            setTimeout(() => setStatus("complete"), 800);
            return prev;
          }
          return prev + 1;
        });
      }, 1200);
      return () => clearInterval(interval);
    }
  }, [status, steps.length]);

  return (
    <div className="relative w-full h-72 md:h-80 flex items-center justify-center p-4">
      <AnimatePresence mode="wait">
        
        {/* IDLE STATE */}
        {status === "idle" && (
          <motion.div
            key="idle"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05, filter: "blur(10px)" }}
            transition={{ duration: 0.5 }}
            className="w-full max-w-md bg-white/60 dark:bg-zinc-900/60 backdrop-blur-xl border border-ink/10 rounded-2xl p-6 shadow-2xl relative z-10"
          >
            <div className="absolute -top-10 -left-10 w-32 h-32 bg-blue/20 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-10 -right-10 w-32 h-32 bg-hotpink/20 rounded-full blur-3xl pointer-events-none" />
            
            <h3 className="text-xl font-display font-bold text-ink mb-4 flex items-center gap-2">
              <Youtube className="w-6 h-6 text-red-500" /> Convert Tutorial
            </h3>
            <div className="relative">
              <input 
                type="text" 
                placeholder="https://youtube.com/watch?v=..." 
                className="w-full bg-white dark:bg-zinc-950 border border-ink/20 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue"
                defaultValue="https://youtube.com/watch?v=dQw4w9WgXcQ"
              />
              <Button 
                onClick={() => {
                  setStatus("processing");
                  setStepIndex(0);
                }}
                className="absolute right-1 top-1 bottom-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg"
              >
                Generate
              </Button>
            </div>
          </motion.div>
        )}

        {/* PROCESSING STATE */}
        {status === "processing" && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05, filter: "blur(10px)" }}
            transition={{ duration: 0.5 }}
            className="w-full max-w-md"
          >
            <div className="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-ink/10 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
              {/* Animated scanning beam */}
              <motion.div 
                className="absolute top-0 bottom-0 w-24 bg-gradient-to-r from-transparent via-blue/10 to-transparent skew-x-12"
                animate={{ left: ["-50%", "150%"] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
              />

              <h3 className="text-lg font-display font-bold text-ink mb-6 flex items-center gap-2">
                <BrainCircuit className="w-5 h-5 text-indigo-500 animate-pulse" /> Factory Processing
              </h3>
              
              <div className="space-y-4">
                {steps.map((step, i) => {
                  const Icon = step.icon;
                  const isActive = i === stepIndex;
                  const isDone = i < stepIndex;
                  return (
                    <motion.div 
                      key={i} 
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className={`flex items-center gap-3 p-3 rounded-lg border transition-all duration-300 ${isActive ? 'bg-blue/10 border-blue/30 shadow-inner' : isDone ? 'bg-green-500/10 border-green-500/20' : 'bg-ink/5 border-transparent opacity-50'}`}
                    >
                      <div className={`p-2 rounded-full ${isActive ? 'bg-blue/20 text-blue' : isDone ? 'bg-green-500/20 text-green-600' : 'bg-ink/10 text-ink-soft'}`}>
                        {isDone ? <CheckCircle2 className="w-4 h-4" /> : <Icon className={`w-4 h-4 ${isActive ? 'animate-spin-slow' : ''}`} />}
                      </div>
                      <span className={`text-sm font-medium ${isActive ? 'text-blue' : isDone ? 'text-green-600' : 'text-ink-soft'}`}>
                        {step.text}
                      </span>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}

        {/* COMPLETE STATE */}
        {status === "complete" && (
          <motion.div
            key="complete"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-lg bg-zinc-950 rounded-2xl shadow-2xl border border-white/10 overflow-hidden flex flex-col relative"
          >
             <div className="absolute inset-0 bg-[linear-gradient(45deg,rgba(99,102,241,0.1),transparent)] pointer-events-none" />
             
             <div className="p-4 border-b border-white/10 flex justify-between items-center bg-zinc-900/50">
                <div className="flex items-center gap-2">
                   <div className="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]" />
                   <span className="text-white font-mono text-xs font-semibold">Ready.</span>
                </div>
                <Button size="sm" variant="outline" onClick={() => setStatus("idle")} className="h-7 text-xs bg-white/10 text-white border-white/20 hover:bg-white/20">
                  Reset Demo
                </Button>
             </div>

             <div className="flex h-48">
                {/* Mock Video Player */}
                <div className="w-1/2 border-r border-white/10 p-2 relative bg-black/50">
                   <div className="w-full h-full rounded bg-zinc-800 flex items-center justify-center relative overflow-hidden">
                      <Play className="w-8 h-8 text-white/50" />
                      <div className="absolute bottom-2 left-2 right-2 h-1 bg-white/20 rounded-full overflow-hidden">
                         <div className="w-1/3 h-full bg-red-500 rounded-full" />
                      </div>
                   </div>
                </div>
                {/* Mock Code Editor */}
                <div className="w-1/2 p-3 font-mono text-[10px] text-lime leading-relaxed opacity-80">
                   <p className="text-purple-400">def <span className="text-blue-400">mastery</span>():</p>
                   <p className="pl-4 text-ink-soft"># Interactive lab generated!</p>
                   <p className="pl-4">return <span className="text-orange-400">"Interactive Curriculum"</span></p>
                   
                   <div className="mt-4 p-2 border border-blue/30 bg-blue/10 rounded">
                      <p className="text-blue-300 font-bold mb-1">Checkpoint</p>
                      <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full border border-blue-400" /> Option A</div>
                      <div className="flex items-center gap-2 mt-1"><div className="w-2 h-2 rounded-full bg-blue-500" /> Option B</div>
                   </div>
                </div>
             </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  );
}
