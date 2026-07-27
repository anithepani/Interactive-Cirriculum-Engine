"use client";

import { motion } from "framer-motion";

interface InteractiveAvatarProps {
  isPasswordFocused: boolean;
  emailLength: number;
}

export function InteractiveAvatar({ isPasswordFocused, emailLength }: InteractiveAvatarProps) {
  // Map email length (0-30 characters) to pupil X translation (-6 to +6 px)
  const maxChars = 30;
  const clampedLength = Math.min(emailLength, maxChars);
  // -8px (looking left when empty) to +8px (looking right when full)
  const pupilX = (clampedLength / maxChars) * 16 - 8;
  
  // When looking at email, look slightly down. When password focused, look straight (behind hands).
  const pupilY = isPasswordFocused ? 0 : 4; 

  return (
    <div className="relative w-32 h-32 mx-auto mb-6 flex justify-center items-end overflow-hidden rounded-full bg-indigo-50 dark:bg-indigo-900/20 border-[6px] border-white dark:border-zinc-800 shadow-inner">
      
      {/* Face Base (Yeti / Panda) */}
      <div className="w-[100px] h-[100px] bg-white dark:bg-zinc-200 rounded-[50px] relative shadow-sm translate-y-2">
        
        {/* Left Eye Container */}
        <div className="absolute left-[14px] top-[24px] w-[28px] h-[32px] bg-zinc-800 rounded-full flex items-center justify-center overflow-hidden">
          <motion.div
            className="w-[12px] h-[12px] bg-white rounded-full shadow-[inset_0_-2px_4px_rgba(0,0,0,0.5)]"
            animate={{ x: pupilX, y: pupilY }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
          />
        </div>

        {/* Right Eye Container */}
        <div className="absolute right-[14px] top-[24px] w-[28px] h-[32px] bg-zinc-800 rounded-full flex items-center justify-center overflow-hidden">
          <motion.div
            className="w-[12px] h-[12px] bg-white rounded-full shadow-[inset_0_-2px_4px_rgba(0,0,0,0.5)]"
            animate={{ x: pupilX, y: pupilY }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
          />
        </div>

        {/* Nose */}
        <div className="absolute left-1/2 top-[60px] -translate-x-1/2 w-[16px] h-[10px] bg-zinc-300 dark:bg-zinc-400 rounded-full" />
        
        {/* Mouth */}
        <div className="absolute left-1/2 top-[76px] -translate-x-1/2 w-[24px] h-[12px] bg-rose-400 rounded-b-full shadow-inner opacity-80" />
      </div>

      {/* Left Hand */}
      <motion.div
        className="absolute w-[44px] h-[64px] bg-white dark:bg-zinc-200 rounded-[22px] shadow-lg border-2 border-zinc-100 dark:border-zinc-300 z-10"
        initial={{ left: -10, bottom: -40, rotate: -20 }}
        animate={{
          left: isPasswordFocused ? 20 : -20,
          bottom: isPasswordFocused ? 28 : -40,
          rotate: isPasswordFocused ? 15 : -30,
        }}
        transition={{ type: "spring", stiffness: 220, damping: 20 }}
      />

      {/* Right Hand */}
      <motion.div
        className="absolute w-[44px] h-[64px] bg-white dark:bg-zinc-200 rounded-[22px] shadow-lg border-2 border-zinc-100 dark:border-zinc-300 z-10"
        initial={{ right: -10, bottom: -40, rotate: 20 }}
        animate={{
          right: isPasswordFocused ? 20 : -20,
          bottom: isPasswordFocused ? 28 : -40,
          rotate: isPasswordFocused ? -15 : 30,
        }}
        transition={{ type: "spring", stiffness: 220, damping: 20 }}
      />
    </div>
  );
}
