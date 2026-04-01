"use client";

import { useState, useMemo } from 'react';
import { formatIndianNumber, cn } from '../../lib/utils';
import { ChevronUp, ChevronDown, Search } from 'lucide-react';

interface DataTableProps {
  data: any[];
  title?: string;
}

export function DataTable({ data, title }: DataTableProps) {
  const [sortConfig, setSortConfig] = useState<{ key: string; dir: 'asc' | 'desc' } | null>(null);
  const [filterQuery, setFilterQuery] = useState('');

  const keys = useMemo(() => {
    if (!data || data.length === 0) return [];
    // Basic keys for NCRB or other datasets
    return Object.keys(data[0]).filter(k => !k.startsWith('_') && k !== 'id');
  }, [data]);

  const filteredAndSortedData = useMemo(() => {
    let result = [...data];

    // Filter
    if (filterQuery) {
      result = result.filter(row => 
        Object.values(row).some(val => 
          String(val).toLowerCase().includes(filterQuery.toLowerCase())
        )
      );
    }

    // Sort
    if (sortConfig) {
      result.sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];
        if (aVal < bVal) return sortConfig.dir === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.dir === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return result;
  }, [data, sortConfig, filterQuery]);

  const requestSort = (key: string) => {
    let dir: 'asc' | 'desc' = 'asc';
    if (sortConfig?.key === key && sortConfig.dir === 'asc') {
      dir = 'desc';
    }
    setSortConfig({ key, dir });
  };

  if (!data?.length) return null;

  return (
    <div className="space-y-4 font-label animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center px-6 pt-4 gap-4">
        <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/60">
          {title || "Registry of Evidence"}
        </h3>
        <div className="relative w-full sm:w-64">
           <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-on-surface-variant/40" />
           <input 
             type="text" 
             placeholder="Search records..."
             value={filterQuery}
             onChange={(e) => setFilterQuery(e.target.value)}
             className="w-full pl-9 pr-4 py-1.5 text-xs bg-surface-container-low border-none rounded-lg focus:ring-1 focus:ring-primary/20 placeholder:text-on-surface-variant/30 text-on-surface"
           />
        </div>
      </div>

      <div className="overflow-x-auto border-t border-outline-variant/10">
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="bg-surface-container-low/30 text-on-surface-variant/40 text-[10px] uppercase tracking-widest font-bold border-b border-outline-variant/10">
              {keys.map((key) => (
                <th 
                  key={key} 
                  onClick={() => requestSort(key)}
                  className="px-6 py-4 cursor-pointer hover:bg-primary/5 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {key.replace(/_/g, ' ')}
                    {sortConfig?.key === key && (
                      sortConfig.dir === 'asc' ? <ChevronUp className="w-3 h-3 text-primary" /> : <ChevronDown className="w-3 h-3 text-primary" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5">
            {filteredAndSortedData.map((row, idx) => (
              <tr 
                key={idx} 
                className="hover:bg-primary/[0.02] transition-colors group"
              >
                {keys.map((key) => {
                  const val = row[key];
                  const isNumber = typeof val === 'number';
                  return (
                    <td 
                      key={key} 
                      className={cn(
                        "px-6 py-4 whitespace-nowrap text-on-surface/80 leading-snug font-medium",
                        isNumber ? "font-mono font-normal text-right tabular-nums bg-primary/[0.01]" : ""
                      )}
                    >
                      {isNumber ? formatIndianNumber(val) : String(val)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {filteredAndSortedData.length === 0 && (
        <div className="p-12 text-center text-on-surface-variant/40 italic text-sm">
          No records matching your search.
        </div>
      )}
    </div>
  );
}
