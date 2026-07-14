/**
 * PageTransition
 * --------------
 * Framer Motion wrapper that provides a smooth fade+slide-up entrance
 * when navigating between pages in the Next.js App Router.
 *
 * Usage (in a page or layout):
 *   <PageTransition>
 *     <YourContent />
 *   </PageTransition>
 *
 * The transition matches the landing page section animations (fadeUp variant).
 */

"use client";

import { motion } from "framer-motion";

interface PageTransitionProps {
  children: React.ReactNode;
  className?: string;
}

const variants = {
  hidden: { opacity: 0, y: 18 },
  enter: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: "easeOut" as const },
  },
  exit: {
    opacity: 0,
    y: -12,
    transition: { duration: 0.25, ease: "easeIn" as const },
  },
};

export default function PageTransition({
  children,
  className,
}: PageTransitionProps) {
  return (
    <motion.div
      variants={variants}
      initial="hidden"
      animate="enter"
      exit="exit"
      className={className}
    >
      {children}
    </motion.div>
  );
}
