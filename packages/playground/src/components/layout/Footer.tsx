"use client";

import Link from "next/link";
import { Github, Database, FileText, Layout, Globe, Shield, Terminal } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-outline-variant/10 bg-background font-sans mt-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center px-8 py-16 max-w-[1440px] mx-auto gap-12">
        <div className="space-y-4 max-w-sm">
          <div className="flex items-center gap-2">
            <img src="/logo_monogram.png" alt="BharatData" className="w-6 h-6 opacity-80" />
            <span className="text-xl font-serif font-bold text-primary italic">BharatData</span>
          </div>
          <p className="text-sm text-on-surface-variant/60 leading-relaxed font-sans">
            Bridging the gap between raw public datasets and actionable insights through high-fidelity data processing.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-12 gap-y-8">
          <div className="flex flex-col gap-3 text-[13px]">
            <span className="text-[10px] uppercase tracking-widest font-bold text-on-surface-variant/40 mb-1">Platform</span>
            <Link href="https://play.bharatdata.dev" className="text-on-surface-variant/70 hover:text-primary transition-colors flex items-center gap-2">
              <Layout className="w-3.5 h-3.5" />
              Playground
            </Link>
            <Link href="https://docs.bharatdata.dev" className="text-on-surface-variant/70 hover:text-primary transition-colors flex items-center gap-2">
              <FileText className="w-3.5 h-3.5" />
              Documentation
            </Link>
            <Link href="https://api.bharatdata.dev" className="text-on-surface-variant/70 hover:text-primary transition-colors flex items-center gap-2">
              <Terminal className="w-3.5 h-3.5" />
              API Access
            </Link>
          </div>
          
          <div className="flex flex-col gap-3 text-[13px]">
            <span className="text-[10px] uppercase tracking-widest font-bold text-on-surface-variant/40 mb-1">Resources</span>
            <Link href="https://docs.bharatdata.dev/lexicon" className="text-on-surface-variant/70 hover:text-primary transition-colors flex items-center gap-2">
              <Database className="w-3.5 h-3.5" />
              Data Lexicon
            </Link>
            <Link href="https://github.com/bharatdata-ai/bharatdata" className="text-on-surface-variant/70 hover:text-primary transition-colors flex items-center gap-2">
              <Github className="w-3.5 h-3.5" />
              GitHub
            </Link>
          </div>

          <div className="flex flex-col gap-3 text-[13px]">
            <span className="text-[10px] uppercase tracking-widest font-bold text-on-surface-variant/40 mb-1">Legal</span>
            <Link href="https://docs.bharatdata.dev/privacy" className="text-on-surface-variant/70 hover:text-primary transition-colors flex items-center gap-2">
              <Shield className="w-3.5 h-3.5" />
              Privacy Policy
            </Link>
            <Link href="https://docs.bharatdata.dev/terms" className="text-on-surface-variant/70 hover:text-primary transition-colors flex items-center gap-2">
              <FileText className="w-3.5 h-3.5" />
              Terms of Service
            </Link>
          </div>
        </div>

        <div className="flex flex-col items-start md:items-end gap-6 self-start md:self-center">
          <div className="text-[10px] text-on-surface-variant/40 uppercase tracking-[0.2em] font-mono">
            © 2026 BHARATDATA TERMINAL INDEX.
          </div>
          <div className="flex gap-6">
            <Globe className="w-5 h-5 text-on-surface-variant/20 hover:text-primary/40 cursor-pointer transition-colors" />
            <Database className="w-5 h-5 text-on-surface-variant/20 hover:text-primary/40 cursor-pointer transition-colors" />
            <Github className="w-5 h-5 text-on-surface-variant/20 hover:text-primary/40 cursor-pointer transition-colors" />
          </div>
        </div>
      </div>
    </footer>
  );
}
