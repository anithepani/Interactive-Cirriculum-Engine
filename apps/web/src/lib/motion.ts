export const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.5, ease: "easeOut" as const },
  }),
};

export const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};

export const cardFanSpring = {
  type: "spring" as const,
  stiffness: 120,
  damping: 14,
};

export const viewportOnce = { once: true, amount: 0.3 } as const;
