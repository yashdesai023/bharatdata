import React, { useState, useEffect } from 'react';
import { AlertCircle, Clock, WifiOff, Database, Info, RefreshCw } from 'lucide-react';
import { cn } from '../../lib/utils';
import { motion } from 'framer-motion';

interface ErrorStateProps {
  type: 'rate-limit' | 'network' | 'database' | 'generic';
  message: string;
  retryAfter?: number;
  onRetry?: () => void;
}

export function ErrorState({ type, message, retryAfter, onRetry }: ErrorStateProps) {
  const [timeLeft, setTimeLeft] = useState(retryAfter || 0);

  useEffect(() => {
    if (timeLeft <= 0) return;
    const timer = setInterval(() => {
      setTimeLeft(prev => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [timeLeft]);

  const config = {
    'rate-limit': {
      icon: Clock,
      color: 'amber',
      title: 'Cooldown Active',
      bg: 'bg-amber-50/50',
      border: 'border-amber-200/50',
      text: 'text-amber-900',
      description: 'text-amber-800/80'
    },
    'network': {
      icon: WifiOff,
      color: 'slate',
      title: 'Connection Lost',
      bg: 'bg-slate-50/50',
      border: 'border-slate-200/50',
      text: 'text-slate-900',
      description: 'text-slate-800/80'
    },
    'database': {
      icon: Database,
      color: 'blue',
      title: 'Legacy Fallback Active',
      bg: 'bg-blue-50/50',
      border: 'border-blue-200/50',
      text: 'text-blue-900',
      description: 'text-blue-800/80'
    },
    'generic': {
      icon: AlertCircle,
      color: 'red',
      title: 'Query Interrupted',
      bg: 'bg-red-50/50',
      border: 'border-red-200/50',
      text: 'text-red-900',
      description: 'text-red-800/80'
    }
  }[type];

  const Icon = config.icon;

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        "p-6 rounded-2xl border flex gap-5 items-start shadow-sm",
        config.bg,
        config.border
      )}
    >
      <div className={cn("p-3 rounded-xl bg-white shadow-sm", `text-${config.color}-600`)}>
        <Icon className="w-6 h-6" />
      </div>
      
      <div className="flex-grow space-y-1">
        <div className="flex items-center justify-between">
          <h3 className={cn("font-bold font-label text-base", config.text)}>{config.title}</h3>
          {timeLeft > 0 && (
            <span className="bg-white/80 px-2 py-0.5 rounded text-[10px] font-bold font-label uppercase tracking-widest text-primary border border-primary/10">
              Refresh in {timeLeft}s
            </span>
          )}
        </div>
        <p className={cn("text-sm leading-relaxed max-w-2xl", config.description)}>
          {message}
        </p>
        
        <div className="pt-3 flex gap-3">
          <button 
            onClick={onRetry}
            disabled={timeLeft > 0}
            className={cn(
              "px-4 py-1.5 rounded-lg text-xs font-bold font-label uppercase tracking-widest transition-all shadow-sm flex items-center gap-2 border",
              timeLeft > 0 
                ? "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed" 
                : "bg-white text-primary border-primary/20 hover:bg-primary/5 active:scale-95"
            )}
          >
            <RefreshCw className={cn("w-3 h-3", timeLeft > 0 ? "opacity-30" : "animate-spin-slow")} />
            {timeLeft > 0 ? `Wait ${timeLeft}s` : 'Retry Query'}
          </button>
          
          <button 
            className="px-4 py-1.5 rounded-lg text-xs font-bold font-label uppercase tracking-widest transition-all text-on-surface-variant hover:bg-black/5"
            onClick={() => window.open('https://github.com/bharatdata/bharatdata', '_blank')}
          >
            Check Status
          </button>
        </div>
      </div>
    </motion.div>
  );
}
