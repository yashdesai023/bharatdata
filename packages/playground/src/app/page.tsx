"use client";

import { useState, useRef, useEffect } from 'react';
import { BharatData } from '@bharatdata/typescript-sdk';
import { AIQueryEvent, AIQueryPlan } from '@bharatdata/typescript-sdk';
import { motion, AnimatePresence } from 'framer-motion';
import { DataTable } from '../components/ui/DataTable';
import { DataChart } from '../components/ui/DataChart';
import { IndiaMap } from '../components/ui/IndiaMap';
import { StructuredQueryBuilder } from '../components/ui/StructuredQueryBuilder';
import { ErrorState } from '../components/ui/ErrorStates';
import { Search, Loader2, Info, ChevronRight, Download, Copy, Share2, Map as MapIcon, Table as TableIcon, BarChart3, AlertCircle, History } from 'lucide-react';
import { cn } from '../lib/utils';
import ReactMarkdown from 'react-markdown';

const bd = new BharatData({ baseUrl: 'http://localhost:8787' });

const EXAMPLES = [
  "Crime trends in Maharashtra 2021-2023",
  "Compare cyber crime across top 5 states",
  "District-wise crimes against women in UP 2023",
];

/**
 * Custom Narrative Renderer to handle Markdown tables without external plugins
 */
function NarrativeRenderer({ content }: { content: string }) {
  if (!content) return null;

  const blocks: { type: 'markdown' | 'table'; content: string }[] = [];
  const lines = content.split('\n');
  let currentBlock: { type: 'markdown' | 'table'; lines: string[] } | null = null;

  lines.forEach((line) => {
    const isTableLine = line.trim().startsWith('|');
    const type = isTableLine ? 'table' : 'markdown';

    if (currentBlock && currentBlock.type === type) {
      currentBlock.lines.push(line);
    } else {
      if (currentBlock) {
        const b = currentBlock as { type: 'markdown' | 'table'; lines: string[] };
        blocks.push({ type: b.type, content: b.lines.join('\n') });
      }
      currentBlock = { type, lines: [line] };
    }
  });

  if (currentBlock) {
    const finalBlock = currentBlock as { type: 'markdown' | 'table'; lines: string[] };
    blocks.push({ type: finalBlock.type, content: finalBlock.lines.join('\n') });
  }

  return (
    <div className="space-y-4">
      {blocks.map((block, i) => {
        if (block.type === 'table') {
          const rows = block.content.trim().split('\n');
          // Standard Markdown table needs at least 2 rows (header + separator)
          if (rows.length >= 2) {
            const parseRow = (row: string) => {
              // Split by | but remove the leading and trailing empty strings from the outer pipes
              const cells = row.split('|');
              return cells.slice(1, -1).map(c => c.trim());
            };

            const headerCells = parseRow(rows[0]);
            const bodyRows = rows.slice(2).map(parseRow);

            return (
              <div key={i} className="overflow-x-auto my-8 rounded-xl border border-outline-variant/20 shadow-sm bg-white/50">
                <table className="w-full border-collapse text-sm">
                  <thead className="bg-surface-container/50 text-primary uppercase text-[10px] font-bold tracking-widest border-b border-outline-variant/10">
                    <tr>
                      {headerCells.map((cell, j) => (
                        <th key={j} className="p-4 text-left font-bold">{cell}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/10">
                    {bodyRows.map((row, j) => (
                      <tr key={j} className="hover:bg-primary/[0.02] transition-colors">
                        {row.map((cell, k) => (
                          <td key={k} className="p-4 text-on-surface-variant font-body">
                            <ReactMarkdown>{cell}</ReactMarkdown>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }
        }
        return (
          <div key={i} className="last:mb-0">
            <ReactMarkdown>
              {block.content}
            </ReactMarkdown>
          </div>
        );
      })}
    </div>
  );
}

export default function PlaygroundPage() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'nl' | 'structured'>('nl');
  const [activeTab, setActiveTab] = useState<'table' | 'chart' | 'map'>('table');
  
  // Response State
  const [queryPlan, setQueryPlan] = useState<AIQueryPlan | null>(null);
  const [data, setData] = useState<any[]>([]);
  const [narrative, setNarrative] = useState("");
  const [errorStatus, setErrorStatus] = useState<{ 
    type: 'rate-limit' | 'network' | 'database' | 'generic', 
    message: string, 
    retryAfter?: number 
  } | null>(null);

  const handleQuery = async (queryOverride?: string) => {
    const q = queryOverride || prompt;
    if (!q.trim()) return;

    setLoading(true);
    setErrorStatus(null);
    setQueryPlan(null);
    setData([]);
    setNarrative("");

    try {
      const generator = bd.queryAI(q);
      for await (const event of generator) {
        if (event.type === 'initial') {
          setQueryPlan(event.queryPlan);
          setData(event.data);
          
          if (event.queryPlan?.chart_type === 'map') setActiveTab('map');
          else if (event.queryPlan?.chart_type !== 'none' && event.queryPlan?.chart_type) setActiveTab('chart');
          else setActiveTab('table');
        } else if (event.type === 'delta') {
          setNarrative(prev => prev + event.content);
        }
      }
    } catch (err: any) {
      if (err.message.includes('Rate Limit')) {
        setErrorStatus({
          type: 'rate-limit',
          message: err.message,
          retryAfter: 60 // Default minute cooldown (Sync with API 10/min)
        });
      } else {
        setErrorStatus({
          type: 'generic',
          message: err.message || "Connection interrupted."
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCSV = () => {
    if (!data || data.length === 0) return;
    
    try {
      // 1. Extract and Sanitize Headers
      const keys = Object.keys(data[0]);
      const headerRow = keys.map(k => `"${k.replace(/"/g, '""')}"`).join(",");
      
      // 2. Map and Sanitize Data Rows
      const dataRows = data.map(record => {
        return keys.map(key => {
          const val = record[key];
          const stringVal = val === null || val === undefined ? '' : String(val);
          return `"${stringVal.replace(/"/g, '""')}"`;
        }).join(",");
      });

      // 3. Assemble and Download
      const csvContent = [headerRow, ...dataRows].join("\n");
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `bharatdata_${queryPlan?.dataset?.toLowerCase() || 'records'}_${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error("CSV Export failed:", err);
      setErrorStatus({ type: 'generic', message: "Failed to generate CSV export. Please try again." });
    }
  };

  const handleGenerateReport = () => {
    if (!prompt) return;
    const reportPrompt = `GENERATE_SCHOLARLY_REPORT: Provide a formal Academic Analysis and Executive Briefing for "${prompt}". Use professional headings and cite the data findings.`;
    handleQuery(reportPrompt);
  };

  const handleVerifySource = () => {
    // Mapping dataset identifiers to official government source portals
    const sourceUrls: Record<string, string> = {
      'ncrb': 'https://ncrb.gov.in/en/crime-in-india',
      'ncrb-crime': 'https://ncrb.gov.in/en/crime-in-india',
      'rbi': 'https://dbie.rbi.org.in/',
      'census': 'https://censusindia.gov.in/'
    };

    const datasetId = queryPlan?.dataset?.toLowerCase() || 'ncrb';
    const url = sourceUrls[datasetId] || 'https://data.gov.in/';
    window.open(url, '_blank');
  };

  const handleExportNarrative = () => {
    if (!narrative) return;
    
    const header = `BHARATDATA INTELLIGENCE REPORT\nGenerated on: ${new Date().toLocaleString()}\nQuery: ${prompt}\nSource: ${queryPlan?.dataset || 'Government Data Registry'}\n--------------------------------------------------\n\n`;
    const footer = `\n\n--------------------------------------------------\nEnd of Report | Prepared by BharatData Intelligence System`;
    const content = header + narrative + footer;
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `bharatdata_report_${new Date().toISOString().split('T')[0]}.txt`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen">
      <main className="pt-20 pb-20 px-6">
        <div className="max-w-[850px] mx-auto flex flex-col items-center">
          
          {/* Section 1: Hero & Query Area */}
          <section className="w-full flex flex-col items-center gap-12 text-center">
            
            <div className="w-full space-y-6">
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-center"
              >
                <img 
                  src="/logo_full.png" 
                  alt="BharatData" 
                  className="h-20 w-auto"
                />
              </motion.div>
              <div className="max-w-2xl mx-auto space-y-4">
                <p className="text-on-surface-variant text-xl leading-relaxed italic">
                  The professional search engine for Indian public data.
                </p>
                <p className="text-on-surface-variant/80 text-sm md:text-base leading-relaxed font-label px-4 tracking-tight">
                  Empowering <span className="font-semibold text-primary">journalists, researchers, and citizens</span> to ask questions about Indian government datasets and receive verified answers with direct source citations.
                </p>
              </div>
            </div>

            {/* Central Query Container */}
            <div className="w-full max-w-3xl">
              <div className="bg-surface-container-lowest rounded-2xl ambient-shadow border border-outline-variant/30 overflow-hidden transition-all duration-300">
                <div className="p-8">
                  {mode === 'nl' ? (
                    <textarea 
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="Search Indian government data..."
                      className="w-full h-20 p-0 bg-transparent border-none focus:ring-0 text-xl text-on-background placeholder-on-surface-variant/30 resize-none font-body text-left leading-relaxed"
                      onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleQuery())}
                    />
                  ) : (
                    <StructuredQueryBuilder onQuery={handleQuery} loading={loading} />
                  )}
                </div>

                <div className="flex flex-col md:flex-row justify-between items-center p-6 bg-surface-container-low/50 border-t border-outline-variant/20 gap-4">
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] font-bold text-on-surface-variant font-label tracking-wide uppercase">Structured Query</span>
                    <button 
                      onClick={() => setMode(mode === 'nl' ? 'structured' : 'nl')}
                      className={cn(
                        "w-10 h-5 rounded-full relative transition-all group",
                        mode === 'structured' ? "bg-primary" : "bg-outline-variant/40"
                      )}
                    >
                      <div className={cn(
                        "absolute top-1 w-3 h-3 bg-white rounded-full transition-all",
                        mode === 'structured' ? "left-6" : "left-1"
                      )} />
                    </button>
                  </div>

                  <button 
                    onClick={() => handleQuery()}
                    disabled={loading || !prompt.trim()}
                    className="bg-primary text-white px-8 py-3.5 rounded-xl font-semibold flex items-center gap-2.5 hover:bg-[#002045] active:scale-[0.98] transition-all shadow-md font-label text-sm tracking-wide disabled:opacity-50"
                  >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <span className="material-symbols-outlined text-[18px]">search</span>}
                    {loading ? 'Analyzing...' : 'Ask Bharat Data'}
                  </button>
                </div>
              </div>
            </div>

            {/* Example Inquiries */}
            {!queryPlan && !loading && (
              <div className="w-full space-y-6">
                <div className="flex items-center justify-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent font-label">Common Inquiries</span>
                </div>
                <div className="flex flex-wrap justify-center gap-3">
                  {EXAMPLES.map((ex) => (
                    <button 
                      key={ex}
                      onClick={() => { setPrompt(ex); handleQuery(ex); }}
                      className="bg-surface-container-low hover:bg-white text-on-surface-variant hover:text-primary px-5 py-2.5 rounded-lg text-sm transition-all duration-200 border border-outline-variant/40 font-label italic"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center justify-center gap-2 text-on-surface-variant/60 text-[11px] font-label tracking-tight">
              <span className="material-symbols-outlined text-[14px]">history_edu</span>
              Bharat Data is an independent open source project. Not affiliated with any government body.
            </div>
          </section>

          {/* Section 2: Response Area */}
          <AnimatePresence>
            {(queryPlan || loading || errorStatus) && (
              <motion.section 
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full mt-24 space-y-20 pb-40"
              >
                {errorStatus && (
                  <ErrorState 
                    type={errorStatus.type}
                    message={errorStatus.message}
                    retryAfter={errorStatus.retryAfter}
                    onRetry={() => handleQuery()}
                  />
                )}

                {/* AI Narrative Narrative */}
                {(narrative || loading) && (
                  <div className="space-y-8">
                    <div className="flex items-center gap-3">
                      <div className="h-[1px] flex-grow bg-gradient-to-r from-transparent via-outline-variant/30 to-transparent" />
                      <span className="text-[10px] font-bold uppercase tracking-[0.3em] text-on-surface-variant/40 font-label">Narrative Analysis</span>
                      <div className="h-[1px] flex-grow bg-gradient-to-r from-transparent via-outline-variant/30 to-transparent" />
                    </div>
                    
                    <div className="text-left font-body text-base md:text-lg leading-relaxed text-on-background/80 min-h-[100px] prose prose-slate max-w-none">
                      <NarrativeRenderer content={narrative} />
                      {loading && <span className="inline-block w-2.5 h-6 bg-primary/20 animate-pulse ml-2 align-middle" />}
                    </div>

                    {queryPlan && (
                      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pt-6 border-t border-outline-variant/10 gap-4 text-[10px] font-label font-bold text-on-surface-variant/40 uppercase tracking-widest">
                        <div className="flex flex-wrap items-center gap-6">
                          <span className="flex items-center gap-1.5"><History className="w-3.5 h-3.5" /> Source: {queryPlan.dataset}</span>
                          <span className="flex items-center gap-1.5 font-bold text-primary/60 italic lowercase bg-primary/5 px-2 py-0.5 rounded">
                             Generated by BharatData Intelligence System
                          </span>
                        </div>
                        <div className="flex items-center gap-4">
                           <button 
                             onClick={handleVerifySource}
                             className="hover:text-primary transition-colors flex items-center gap-1.5 p-1 px-2 border border-transparent hover:border-outline-variant/30 rounded-lg"
                           >
                             <Search className="w-3 h-3"/> Verify Source
                           </button>
                           <button 
                             onClick={handleExportNarrative}
                             className="hover:text-primary transition-colors flex items-center gap-1.5 p-1 px-2 border border-transparent hover:border-outline-variant/30 rounded-lg"
                           >
                             <Share2 className="w-3 h-3"/> Export Narrative
                           </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Visualizations Section */}
                {data && data.length > 0 && (
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="space-y-12"
                  >
                    <div className="flex items-center justify-between sticky top-[65px] z-40 bg-background/80 backdrop-blur-md py-4 border-b border-outline-variant/10">
                      <div className="space-y-1">
                        <div className="flex items-center gap-3">
                          <h2 className="text-2xl font-bold font-headline text-primary italic">
                            Extracted Intelligence
                          </h2>
                          {queryPlan?.queryComplexity && (
                            <span className={cn(
                              "px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-widest border",
                              queryPlan.queryComplexity === 'trend' ? "bg-blue-50 text-blue-700 border-blue-200" :
                              queryPlan.queryComplexity === 'comparison' ? "bg-orange-50 text-orange-700 border-orange-200" :
                              queryPlan.queryComplexity === 'ranking' ? "bg-green-50 text-green-700 border-green-200" :
                              "bg-surface-container-low text-on-surface-variant border-outline-variant/30"
                            )}>
                              {queryPlan.queryComplexity}
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] font-bold font-label uppercase text-on-surface-variant/60 tracking-widest">
                          Aggregation: {queryPlan?.level || 'Statewide'} • {(data || []).length} Records Detected
                        </p>
                      </div>
                      
                      <div className="flex bg-surface-container-low p-1 rounded-xl border border-outline-variant/20">
                         {[
                           { id: 'map', icon: MapIcon, label: 'Geo Intelligence' },
                           { id: 'chart', icon: BarChart3, label: 'Trend Analysis' },
                           { id: 'table', icon: TableIcon, label: 'Data Registry' }
                         ].map((tab) => (
                           <button 
                             key={tab.id}
                             onClick={() => setActiveTab(tab.id as any)}
                             className={cn(
                               "flex items-center gap-2 px-4 py-2 rounded-lg transition-all font-label text-xs font-bold uppercase tracking-tight",
                               activeTab === tab.id 
                                 ? "bg-white text-primary shadow-sm ring-1 ring-black/5" 
                                 : "text-on-surface-variant/60 hover:text-primary hover:bg-white/50"
                             )}
                           >
                             <tab.icon className="w-4 h-4"/>
                             <span className="hidden md:inline">{tab.label}</span>
                           </button>
                         ))}
                      </div>
                    </div>

                    <div 
                      key={`${queryPlan?.dataset}-${queryPlan?.level}-${data?.length}`}
                      className="ambient-shadow rounded-2xl border border-outline-variant/30 bg-surface-container-lowest overflow-hidden min-h-[500px]"
                    >
                      {activeTab === 'table' && <DataTable data={data || []} />}
                      {activeTab === 'chart' && (
                        <div className="p-8">
                          <DataChart 
                            key={`chart-${queryPlan?.dataset}`}
                            data={data || []} 
                            type={queryPlan?.chart_type === 'line' ? 'line' : 'bar'} 
                            metric="total_cases"
                            category={
                              queryPlan?.trend 
                                ? 'year' 
                                : Array.isArray(queryPlan?.filters?.category) 
                                ? 'category_label' 
                                : queryPlan?.level === 'state' ? 'state' : 'district'
                            }
                          />
                        </div>
                      )}
                      {activeTab === 'map' && (
                        <IndiaMap 
                          key={`map-${queryPlan?.dataset}`}
                          data={data || []} 
                          metric="total_cases"
                          category={queryPlan?.level === 'state' ? 'state' : 'district'}
                        />
                      )}
                    </div>

                     <div className="flex justify-center gap-4 pt-8">
                        <button 
                          onClick={handleDownloadCSV}
                          disabled={!data || data.length === 0}
                          className="bg-surface-container-low hover:bg-white hover:shadow-md border border-outline-variant/30 px-6 py-2.5 rounded-xl font-label text-xs font-bold uppercase tracking-widest transition-all text-on-surface-variant disabled:opacity-40 disabled:cursor-not-allowed group flex items-center gap-2"
                        >
                          <Download className="w-3.5 h-3.5 group-hover:animate-bounce" />
                          Download raw records (CSV)
                        </button>
                        <button 
                          onClick={handleGenerateReport}
                          disabled={loading || !prompt}
                          className="bg-primary text-white hover:bg-[#002045] px-8 py-2.5 rounded-xl font-label text-xs font-bold uppercase tracking-widest transition-all shadow-lg active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />}
                          Generate Scholarly Report
                        </button>
                     </div>
                  </motion.div>
                )}
              </motion.section>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

