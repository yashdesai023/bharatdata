"use client";

import Link from "next/link";

export function Footer() {
  return (
    <footer className="w-full border-t border-outline-variant/20 bg-background font-label mt-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center px-8 py-16 max-w-7xl mx-auto gap-12">
        <div className="space-y-4 max-w-sm">
          <div className="text-2xl font-headline font-bold text-primary italic">BharatData</div>
          <p className="text-sm text-on-surface-variant leading-relaxed opacity-80">
            Bridging the gap between raw public datasets and actionable insights through high-fidelity data processing.
          </p>
        </div>

        <div className="flex flex-wrap gap-x-12 gap-y-6">
          <div className="flex flex-col gap-3 text-sm">
            <Link href="/about" className="text-on-surface-variant hover:text-primary transition-colors">About</Link>
            <Link href="/datasets" className="text-on-surface-variant hover:text-primary transition-colors">Data Lexicon</Link>
            <Link href="/documentation" className="text-on-surface-variant hover:text-primary transition-colors">Documentation</Link>
          </div>
          <div className="flex flex-col gap-3 text-sm">
            <Link href="/privacy" className="text-on-surface-variant hover:text-primary transition-colors">Privacy Policy</Link>
            <Link href="/terms" className="text-on-surface-variant hover:text-primary transition-colors">Terms of Service</Link>
            <Link href="/api" className="text-on-surface-variant hover:text-primary transition-colors">API Access</Link>
          </div>
        </div>

        <div className="flex flex-col items-start md:items-end gap-6">
          <div className="text-[11px] text-on-surface-variant/70 uppercase tracking-widest font-bold">
            © {new Date().getFullYear()} BharatData Playground.
          </div>
          <div className="flex gap-6">
            <span className="material-symbols-outlined text-on-surface-variant/50 cursor-pointer hover:text-primary transition-colors text-xl">language</span>
            <span className="material-symbols-outlined text-on-surface-variant/50 cursor-pointer hover:text-primary transition-colors text-xl">database</span>
            <span className="material-symbols-outlined text-on-surface-variant/50 cursor-pointer hover:text-primary transition-colors text-xl">share</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
