"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { PRICING_COPY, PRICING_TIERS } from "@/lib/data";
import { fadeUp, staggerContainer, viewportOnce } from "@/lib/motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function PricingNodes() {
  return (
    <section id="pricing" className="bg-canvas px-6 py-16 md:py-24">
      <div className="mx-auto grid max-w-container gap-12 md:grid-cols-2 md:items-start">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          variants={staggerContainer}
        >
          <motion.h2 variants={fadeUp} custom={0} className="font-display text-4xl font-bold text-ink">
            {PRICING_COPY.heading}
          </motion.h2>
          <motion.p variants={fadeUp} custom={1} className="mt-4 text-ink-soft">
            {PRICING_COPY.body}
          </motion.p>
          <motion.ul variants={fadeUp} custom={2} className="mt-6 space-y-2 text-sm text-ink-soft">
            {PRICING_COPY.bullets.map((b) => (
              <li key={b} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-lime" />
                {b}
              </li>
            ))}
          </motion.ul>
        </motion.div>

        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-stretch sm:justify-center">
          {PRICING_TIERS.map((tier) => (
            <motion.article
              key={tier.id}
              className={`relative flex w-full flex-col rounded-xl2 p-6 shadow-card sm:max-w-[220px] ${tier.className} ${tier.rotate} sm:rotate-0`}
              whileHover={{ rotate: 0, scale: 1.05, zIndex: 20 }}
              transition={{ type: "spring", stiffness: 200, damping: 18 }}
            >
              {tier.badge && (
                <Badge
                  variant="lime"
                  className="absolute -right-3 -top-3 rotate-6 shadow-md"
                >
                  {tier.badge}
                </Badge>
              )}
              {tier.ribbon && (
                <div className="pointer-events-none absolute -right-8 top-6 w-32 rotate-45 bg-lime py-1 text-center font-mono text-xs font-bold text-ink">
                  {tier.ribbon}
                </div>
              )}
              <p className="font-mono text-sm uppercase tracking-wider opacity-80">{tier.name}</p>
              <p className="mt-2 font-display text-3xl font-black">
                {tier.price}
                <span className="text-base font-normal">{tier.period}</span>
              </p>
              <ul className="mt-4 flex-1 space-y-2 text-xs leading-relaxed">
                {tier.features.map((f) => (
                  <li key={f}>• {f}</li>
                ))}
              </ul>
              <Button
                asChild
                variant={tier.highlight ? "default" : "outline"}
                className={`mt-6 w-full ${tier.highlight ? "bg-white text-orange hover:bg-white/90" : ""}`}
              >
                <Link href="/upload">Choose {tier.name}</Link>
              </Button>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
