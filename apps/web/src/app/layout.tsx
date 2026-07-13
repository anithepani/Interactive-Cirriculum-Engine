import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "@/app/globals.css"; // ✅ changed to relative import
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ThemeProviders from "@/components/ThemeProviders";
import { PRODUCT } from "@/lib/data";

// Space Grotesk supports weights: 300, 400, 500, 600, 700, variable
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: `${PRODUCT.shortName} — ${PRODUCT.tagline}`,
  description: PRODUCT.subTagline,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable}`}
    >
      <body className="min-h-screen bg-canvas font-body text-ink antialiased" suppressHydrationWarning>
        <ThemeProviders>
          <div className="flex min-h-screen flex-col bg-canvas">
            <Navbar />
            <main className="flex-1 pt-16">{children}</main>
            <Footer />
          </div>
        </ThemeProviders>
      </body>
    </html>
  );
}