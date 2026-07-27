"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Github, Linkedin, Twitter, Youtube } from "lucide-react";
import { FOOTER_COLUMNS, PRODUCT, SOCIAL_LINKS } from "@/lib/data";
import { Separator } from "@/components/ui/separator";

const SOCIAL_ICONS = {
  GitHub: Github,
  Twitter: Twitter,
  LinkedIn: Linkedin,
  YouTube: Youtube,
} as const;

export default function Footer() {
  const pathname = usePathname();
  const isAppRoute = /^\/(dashboard|exercises|progress|settings|upload|curriculum|support|discover|curricula|reader)/.test(pathname || "");

  const isAuthRoute = pathname === "/login" || pathname === "/signup";
  if (isAppRoute || isAuthRoute) return null;

  return (
    <footer id="contact" className="bg-canvas px-6 py-16">
      <div className="mx-auto max-w-container">
        <p className="font-display text-3xl font-bold text-ink">Our platform, your code.</p>

        <div className="mt-8 flex flex-wrap gap-3">
          {SOCIAL_LINKS.map((social) => {
            const Icon = SOCIAL_ICONS[social.label as keyof typeof SOCIAL_ICONS];
            return (
              <a
                key={social.label}
                href={social.href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-10 w-10 items-center justify-center rounded-full border border-ink/10 text-ink transition hover:border-ink/30 hover:bg-ink/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30"
                aria-label={social.label}
              >
                <Icon className="h-4 w-4" />
              </a>
            );
          })}
        </div>

        <div className="mt-12 grid grid-cols-2 gap-8 md:grid-cols-4">
          {FOOTER_COLUMNS.map((column, i) => (
            <nav key={i} className="flex flex-col gap-3 text-sm" aria-label={`Footer column ${i + 1}`}>
              {column.links.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  className="text-ink-soft transition hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30 focus-visible:rounded"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          ))}
        </div>

        <Separator className="my-10" />

        <p className="text-sm text-ink-soft">
          © {new Date().getFullYear()} {PRODUCT.name}. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
