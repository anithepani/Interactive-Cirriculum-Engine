import type { Metadata } from "next";
import "@babel/generator"  // Make sure the file is named globals.css
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Interactive Curriculum Engine",
  description: "Interactive video curricula with checkpoints and exercises",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-gray-950 text-gray-100 antialiased min-h-screen">
        <Navbar />
        {children}
      </body>
    </html>
  );
}