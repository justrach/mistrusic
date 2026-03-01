import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geist = Geist({ variable: "--font-geist", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Mistrusic",
  description: "Mistral-powered music generator",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${geist.variable} antialiased bg-black text-white`}>
        <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4 border-b border-white/5 bg-black/60 backdrop-blur-md">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/30">
              <span className="text-[10px] font-bold text-white">M</span>
            </div>
            <Link href="/" className="font-semibold tracking-tight text-white text-sm hover:text-violet-300 transition-colors">
              Mistrusic
            </Link>
          </div>
          <div className="flex items-center gap-1">
            <Link href="/" className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-white hover:bg-white/5 transition-all">
              Generate
            </Link>
            <Link href="/studio" className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-white hover:bg-white/5 transition-all">
              Studio
            </Link>
            <Link href="/arch" className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-white hover:bg-white/5 transition-all">
              Architecture
            </Link>
            <div className="ml-2 flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-violet-500/30 bg-violet-950/40 text-[10px] text-violet-400 font-medium">
              <div className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
              Mistral Hackathon 2025
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
