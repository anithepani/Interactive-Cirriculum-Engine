import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "@/app/globals.css"; // ✅ changed to relative import
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import MainContent from "@/components/MainContent";
import ThemeProviders from "@/components/ThemeProviders";
import { NotificationsProvider } from "@/components/NotificationsProvider";
import { PRODUCT } from "@/lib/data";
import { FilmGrain } from "@/components/ui/FilmGrain";

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
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var m=localStorage.getItem('ice-theme');if(m==='dark'){document.documentElement.classList.add('dark');}}catch(e){}})();`,
          }}
        />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&icon_names=help_center" />
        <style dangerouslySetInnerHTML={{ __html: `
          .material-symbols-outlined {
            font-variation-settings:
            'FILL' 0,
            'wght' 400,
            'GRAD' 0,
            'opsz' 24
          }
        ` }} />
      </head>
      <body className="min-h-screen bg-canvas font-body text-ink antialiased" suppressHydrationWarning>
        <ThemeProviders>
          <NotificationsProvider>
            <div className="flex min-h-screen flex-col bg-canvas">
              <FilmGrain />
              <Navbar />
              <MainContent>{children}</MainContent>
              <Footer />
            </div>
          </NotificationsProvider>
        </ThemeProviders>
      </body>
    </html>
  );
}