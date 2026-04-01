"use client";

import Link from "next/link";

export function Header() {
  return (
    <header className="glass-header">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex flex-col">
          <Link href="/" className="text-2xl font-headline font-bold text-primary italic leading-tight">
            BharatData
          </Link>
          <span className="text-[9px] text-on-surface-variant/60 uppercase tracking-[0.2em] leading-none font-label font-bold mt-0.5">
            Public Data Intelligence
          </span>
        </div>

        <nav className="flex items-center gap-8 text-sm font-label font-medium text-on-surface-variant">
          <Link href="/datasets" className="hover:text-primary transition-colors">Lexicon</Link>
          <Link href="/about" className="hover:text-primary transition-colors">Foundations</Link>
          <button 
            onClick={() => window.open('https://github.com', '_blank')}
            className="bg-primary/5 text-primary px-4 py-1.5 rounded-full hover:bg-primary/10 transition-all font-semibold text-xs border border-primary/10"
          >
            API Access
          </button>
        </nav>
      </div>
    </header>
  );
}
