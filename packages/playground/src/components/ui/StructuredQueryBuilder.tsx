"use client";

import { useState, useMemo } from 'react';
import { cn } from '../../lib/utils';
import { Check, ChevronDown, Database, Filter, Calendar } from 'lucide-react';

interface StructuredQueryBuilderProps {
  onQuery: (query: any) => void;
  loading: boolean;
}

const DATASETS = [
  { id: 'ncrb-crime-india', name: 'NCRB: Crime in India' },
];

const LEVELS = [
  { id: 'state', name: 'State Level' },
  { id: 'district', name: 'District Level' },
];

const CATEGORIES = [
  "Rape",
  "Kidnapping & Abduction",
  "Murder",
  "Cyber Crimes",
  "Crimes against Children"
];

const YEARS = [2023, 2022, 2021, 2020, 2019, 2018];

export function StructuredQueryBuilder({ onQuery, loading }: StructuredQueryBuilderProps) {
  const [selectedDataset, setSelectedDataset] = useState(DATASETS[0].id);
  const [selectedLevel, setSelectedLevel] = useState(LEVELS[0].id);
  const [selectedYear, setSelectedYear] = useState(YEARS[0]);
  const [selectedCategory, setSelectedCategory] = useState(CATEGORIES[0]);

  const handleSubmit = () => {
    // Generate a natural language prompt from these selections to reuse the AI pipeline
    // or call a specific structured endpoint if available.
    // For now, let's generate a prompt:
    const prompt = `${selectedCategory} in all states for the year ${selectedYear} from ${selectedDataset}`;
    onQuery(prompt);
  };

  return (
    <div className="bg-transparent space-y-8 animate-in fade-in slide-in-from-top-4 duration-500">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* Dataset Selection */}
        <div className="space-y-3">
          <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/50 flex items-center gap-2 font-label">
            <Database className="w-3 h-3" /> Dataset Repository
          </label>
          <select 
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            className="w-full bg-surface-container-low/50 border-none rounded-xl py-3 px-4 text-xs focus:ring-1 focus:ring-primary/20 cursor-pointer font-label font-bold text-on-surface appearance-none"
          >
            {DATASETS.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>

        {/* Level Selection */}
        <div className="space-y-3">
          <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/50 flex items-center gap-2 font-label">
            <Filter className="w-3 h-3" /> Spatial Resolution
          </label>
          <select 
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value)}
            className="w-full bg-surface-container-low/50 border-none rounded-xl py-3 px-4 text-xs focus:ring-1 focus:ring-primary/20 cursor-pointer font-label font-bold text-on-surface appearance-none"
          >
            {LEVELS.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        </div>

        {/* Category Selection */}
        <div className="space-y-3">
          <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/50 flex items-center gap-2 font-label">
            <Filter className="w-3 h-3" /> Semantic Category
          </label>
          <select 
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full bg-surface-container-low/50 border-none rounded-xl py-3 px-4 text-xs focus:ring-1 focus:ring-primary/20 cursor-pointer font-label font-bold text-on-surface appearance-none"
          >
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* Year Selection */}
        <div className="space-y-3">
          <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/50 flex items-center gap-2 font-label">
            <Calendar className="w-3 h-3" /> Temporal Range
          </label>
          <select 
            value={selectedYear}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            className="w-full bg-surface-container-low/50 border-none rounded-xl py-3 px-4 text-xs focus:ring-1 focus:ring-primary/20 cursor-pointer font-label font-bold text-on-surface appearance-none"
          >
            {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>

      </div>

      <div className="flex justify-center">
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="bg-surface-container-lowest text-primary px-10 py-3 rounded-full font-bold shadow-sm hover:shadow-md border border-outline-variant/30 disabled:opacity-50 transition-all active:scale-95 flex items-center gap-2.5 font-label text-[11px] uppercase tracking-widest"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin text-primary" /> : <div className="material-symbols-outlined text-[18px]">rebase_edit</div>}
          Synthesize Data Request
        </button>
      </div>
    </div>
  );
}

function Loader2({ className }: { className?: string }) {
  return (
    <svg 
      className={cn("animate-spin", className)} 
      xmlns="http://www.w3.org/2000/svg" 
      fill="none" 
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  );
}
