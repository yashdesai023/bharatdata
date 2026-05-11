"use client";

import { useState, useRef, useEffect, useCallback } from 'react';
import { BharatData } from '@bharatdata/typescript-sdk';
import { AIQueryPlan } from '@bharatdata/typescript-sdk';
import { motion, AnimatePresence } from 'framer-motion';
import { DataTable } from '../components/ui/DataTable';
import { DataChart } from '../components/ui/DataChart';
import { IndiaMap } from '../components/ui/IndiaMap';
import { Search, Loader2, Download, Map as MapIcon, Table as TableIcon, BarChart3, MoreHorizontal, Fullscreen, Send, BarChart, X, Sparkles, MessageCircle, Bot, Zap, TrendingUp } from 'lucide-react';
import { cn } from '../lib/utils';

// Get API URL - support both localhost and production
const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'play.bharatdata.dev') return 'https://api.bharatdata.dev';
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') return 'http://localhost:8787';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'https://api.bharatdata.dev';
};

const bd = new BharatData({ baseUrl: getApiUrl() });

const EXAMPLES = [
  "Show literacy rate across India 2011",
  "Population of top 5 states in 2001",
  "Compare worker ratio between Gujarat and Maharashtra",
];

// Types for chat messages
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  queryPlan?: AIQueryPlan;
  data?: any[];
  isLoading?: boolean;
  needsVisualization?: boolean;
}

// Detect if query needs visualization
function needsVisualization(query: string): boolean {
  const lowerQuery = query.toLowerCase();
  const vizKeywords = [
    'show', 'compare', 'trend', 'chart', 'map', 'graph', 'visual',
    'distribution', 'top', 'bottom', 'ranking', 'percent', 'rate',
    'population', 'literacy', 'workers', 'distribution', 'across',
    'between', 'demographics', 'region', 'state', 'district'
  ];
  return vizKeywords.some(keyword => lowerQuery.includes(keyword));
}

// Detect if user explicitly asks for visualization
function wantsVisualization(query: string): boolean {
  const lowerQuery = query.toLowerCase();
  const explicitViz = ['show chart', 'show map', 'visualize', 'show graph',
    'display as', 'draw', 'plot', 'visualization', 'show data'];
  return explicitViz.some(phrase => lowerQuery.includes(phrase));
}

// Animated Title Component
function AnimatedTitle() {
  const [displayText, setDisplayText] = useState("");
  const [showCursor, setShowCursor] = useState(true);

  const fullText = "BharatData";
  const altText = "Indian Data Infrastructure";

  useEffect(() => {
    let textIndex = 0;
    let isDeleting = false;
    let isAltText = false;
    let timeoutId: NodeJS.Timeout;

    const targetText = () => isAltText ? altText : fullText;

    const animate = () => {
      if (!isDeleting) {
        // Typing
        const currentText = targetText();
        setDisplayText(currentText.substring(0, textIndex + 1));
        textIndex++;

        if (textIndex < currentText.length) {
          timeoutId = setTimeout(animate, 100);
        } else {
          // Finished typing, wait then start deleting
          timeoutId = setTimeout(() => {
            isDeleting = true;
            animate();
          }, 2000);
        }
      } else {
        // Deleting - use backspace effect
        if (textIndex > 0) {
          setDisplayText(targetText().substring(0, textIndex - 1));
          textIndex--;
          timeoutId = setTimeout(animate, 50);
        } else {
          // Finished deleting, switch to other text
          isDeleting = false;
          isAltText = !isAltText;
          textIndex = 0;
          timeoutId = setTimeout(animate, 500);
        }
      }
    };

    // Start animation after a brief delay
    timeoutId = setTimeout(animate, 500);

    // Cursor blinking
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 530);

    return () => {
      clearTimeout(timeoutId);
      clearInterval(cursorInterval);
    };
  }, []);

  return (
    <h1 className="text-5xl md:text-7xl font-bold text-[#8f4e00] tracking-tight font-serif">
      {displayText}
      <span className={cn(
        "inline-block w-[3px] h-[0.9em] bg-[#8f4e00] ml-1 align-middle",
        showCursor ? "opacity-100" : "opacity-0"
      )} />
    </h1>
  );
}

export default function PlaygroundPage() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'table' | 'chart' | 'map'>('table');
  const [showVisualization, setShowVisualization] = useState(false);
  const [userRequestedViz, setUserRequestedViz] = useState(false);

  // Chat messages state
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Response State
  const [queryPlan, setQueryPlan] = useState<AIQueryPlan | null>(null);
  const [data, setData] = useState<any[]>([]);

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const handleQuery = async (queryOverride?: string) => {
    const q = queryOverride || prompt;
    if (!q.trim()) return;

    const isComplexQuery = needsVisualization(q);
    const userWantsViz = wantsVisualization(q);

    // Add user message to chat
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: q,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Add empty AI message placeholder
    const aiMessageId = (Date.now() + 1).toString();
    const aiMessage: ChatMessage = {
      id: aiMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
      needsVisualization: isComplexQuery,
    };
    setMessages(prev => [...prev, aiMessage]);

    // Show visualization for complex queries or if user explicitly asks
    if (isComplexQuery || userWantsViz) {
      setShowVisualization(true);
      if (userWantsViz) setUserRequestedViz(true);
    }

    setLoading(true);
    setPrompt("");

    try {
      const generator = bd.queryAI(q);
      let fullNarrative = "";

      for await (const event of generator) {
        if (event.type === 'initial') {
          setQueryPlan(event.queryPlan);
          setData(event.data);

          setMessages(prev => prev.map(msg =>
            msg.id === aiMessageId
              ? { ...msg, queryPlan: event.queryPlan, data: event.data, isLoading: false }
              : msg
          ));

          if (event.queryPlan?.chart_type === 'map') setActiveTab('map');
          else if (event.queryPlan?.chart_type !== 'none' && event.queryPlan?.chart_type) setActiveTab('chart');
        } else if (event.type === 'delta') {
          fullNarrative += event.content;

          setMessages(prev => prev.map(msg =>
            msg.id === aiMessageId
              ? { ...msg, content: fullNarrative }
              : msg
          ));
        }
      }
    } catch (err: any) {
      setMessages(prev => prev.map(msg =>
        msg.id === aiMessageId
          ? { ...msg, content: `Error: ${err.message || "Connection interrupted."}`, isLoading: false }
          : msg
      ));
    } finally {
      setLoading(false);
      setMessages(prev => prev.map(msg =>
        msg.id === aiMessageId
          ? { ...msg, isLoading: false }
          : msg
      ));
    }
  };

  const handleShowVisualization = () => {
    setShowVisualization(true);
    setUserRequestedViz(true);
  };

  const handleHideVisualization = () => {
    setShowVisualization(false);
  };

  const handleDownloadCSV = () => {
    if (!data || data.length === 0) return;

    try {
      const keys = Object.keys(data[0]);
      const headerRow = keys.map(k => `"${k.replace(/"/g, '""')}"`).join(",");

      const dataRows = data.map(record => {
        return keys.map(key => {
          const val = record[key];
          const stringVal = val === null || val === undefined ? '' : String(val);
          return `"${stringVal.replace(/"/g, '""')}"`;
        }).join(",");
      });

      const csvContent = [headerRow, ...dataRows].join("\n");
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `bharatdata_${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error("CSV Export failed:", err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuery();
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-1 overflow-hidden w-full h-screen bg-[#fff8f5]">
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Hero Section - Only show when no messages */}
        {!hasMessages && (
          <div className="flex-1 flex flex-col items-center justify-center p-8">
            {/* Logo / Title with Animation */}
            <div className="text-center space-y-4 mb-8">
              <AnimatedTitle />
              <p className="text-lg text-[#554336] italic font-serif max-w-xl mx-auto">
                The professional search engine for Indian public data.
              </p>
              <p className="text-sm text-[#554336]/70 max-w-lg mx-auto font-sans">
                Empowering journalists, researchers, and citizens to ask questions about Indian government datasets and receive verified answers with direct source citations.
              </p>

              {/* Feature badges */}
              <div className="flex justify-center gap-4 mt-6">
                <div className="flex items-center gap-2 text-xs text-[#8f4e00] bg-[#fff1e8] px-3 py-1.5 rounded-full border border-[#dbc2b0]">
                  <Zap className="w-3.5 h-3.5" /> AI-Powered
                </div>
                <div className="flex items-center gap-2 text-xs text-[#8f4e00] bg-[#fff1e8] px-3 py-1.5 rounded-full border border-[#dbc2b0]">
                  <TrendingUp className="w-3.5 h-3.5" /> Live Data
                </div>
                <div className="flex items-center gap-2 text-xs text-[#8f4e00] bg-[#fff1e8] px-3 py-1.5 rounded-full border border-[#dbc2b0]">
                  <MessageCircle className="w-3.5 h-3.5" /> Natural Language
                </div>
              </div>
            </div>

            {/* Search Box - Creative Design */}
            <div className="w-full max-w-2xl">
              <div className="bg-white rounded-2xl border-2 border-[#dbc2b0] shadow-xl overflow-hidden relative">
                {/* Decorative gradient line */}
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#8f4e00] via-[#ff9933] to-[#8f4e00]" />

                <div className="p-6">
                  <textarea
                    ref={inputRef}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="w-full h-12 bg-transparent border-none focus:ring-0 focus:outline-none text-lg text-[#231a13] placeholder-[#554336]/50 resize-none font-sans"
                    placeholder="Ask about Indian census data, demographics, statistics..."
                    rows={1}
                  />
                </div>

                <div className="flex justify-between items-center p-4 bg-[#faf5ef] border-t border-[#f1dfd3]">
                  <div className="flex items-center gap-3">
                    <span className="text-xs uppercase tracking-wider text-[#554336] font-medium">AI Query Mode</span>
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  </div>
                  <button
                    onClick={() => handleQuery()}
                    disabled={!prompt.trim() || loading}
                    className="bg-[#8f4e00] text-white px-8 py-3 rounded-xl font-semibold flex items-center gap-2.5 hover:bg-[#693800] transition-all shadow-lg shadow-[#8f4e00]/20 hover:shadow-[#8f4e00]/30 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Search className="w-5 h-5" />
                    )}
                    <span className="font-medium">Ask BharatData</span>
                  </button>
                </div>
              </div>

              {/* Example Queries */}
              <div className="mt-8 space-y-3">
                <div className="flex items-center justify-center gap-2">
                  <span className="text-xs uppercase tracking-wider text-[#8f4e00] font-bold">Try These</span>
                </div>
                <div className="flex flex-wrap justify-center gap-3">
                  {EXAMPLES.map((example, i) => (
                    <button
                      key={i}
                      onClick={() => handleQuery(example)}
                      className="bg-white text-[#554336] px-5 py-2.5 rounded-xl text-sm border-2 border-[#f1dfd3] hover:border-[#8f4e00] hover:text-[#8f4e00] transition-all shadow-sm hover:shadow-md font-sans"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Chat Interface - Shows after first message */}
        {hasMessages && (
          <div className="flex-1 flex overflow-hidden">
            {/* Left Panel: Chat */}
            <div className="w-full md:w-1/2 flex flex-col h-full border-r border-[#e8d7cb] bg-[#fdfcfb]">
              {/* Header */}
              <div className="p-4 border-b border-[#e8d7cb] bg-white flex justify-between items-center flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#8f4e00] to-[#ff9933] flex items-center justify-center text-white shadow-lg">
                    <Bot className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-[#231a13] font-serif">Analysis Session</h3>
                    <p className="text-xs text-[#554336]">Powered by BharatData AI</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {showVisualization && (
                    <button
                      onClick={handleHideVisualization}
                      className="text-xs text-[#554336] hover:text-[#8f4e00] flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-[#fff1e8] transition-colors"
                    >
                      <X className="w-4 h-4" /> Hide Viz
                    </button>
                  )}
                  <button className="text-[#554336] hover:text-[#8f4e00] p-2 rounded-lg hover:bg-[#fff1e8] transition-colors">
                    <MoreHorizontal className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Chat Messages */}
              <div
                ref={chatContainerRef}
                className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 bg-[#fdfcfb]"
              >
                {messages.map((message, idx) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className={message.role === 'user' ? 'flex flex-col items-end gap-2' : 'flex flex-col items-start gap-2'}
                  >
                    {/* User Message */}
                    {message.role === 'user' && (
                      <>
                        <div className="bg-gradient-to-br from-[#8f4e00] to-[#a65c00] text-white p-4 rounded-2xl rounded-tr-sm max-w-[85%] shadow-lg shadow-[#8f4e00]/20">
                          <p className="text-base font-sans">{message.content}</p>
                        </div>
                        <span className="text-xs uppercase tracking-wider text-[#554336]/60 font-medium">{formatTime(message.timestamp)}</span>
                      </>
                    )}

                    {/* AI Response */}
                    {message.role === 'assistant' && (
                      <>
                        <div className="flex items-center gap-3 mb-1">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#8f4e00] to-[#ff9933] flex items-center justify-center text-white shadow-md">
                            <Bot className="w-4 h-4" />
                          </div>
                          <span className="text-xs uppercase tracking-wider text-[#8f4e00] font-bold">BharatData AI</span>
                        </div>

                        {/* Query Indicators */}
                        {message.queryPlan && !message.isLoading && (
                          <div className="flex flex-wrap gap-2 mb-3">
                            {message.queryPlan.entity && (
                              <div className="bg-[#fff1e8] text-[#8f4e00] px-3 py-1.5 rounded-full text-xs font-semibold border border-[#f1dfd3] flex items-center gap-1.5">
                                <span className="material-symbols-outlined text-sm">category</span> {message.queryPlan.entity}
                              </div>
                            )}
                            {message.queryPlan.years && (
                              <div className="bg-[#fff1e8] text-[#8f4e00] px-3 py-1.5 rounded-full text-xs font-semibold border border-[#f1dfd3] flex items-center gap-1.5">
                                <span className="material-symbols-outlined text-sm">calendar_today</span> {message.queryPlan.years[0]}
                              </div>
                            )}
                          </div>
                        )}

                        <div className="bg-white text-[#231a13] p-5 rounded-2xl rounded-tl-sm max-w-[90%] border border-[#f1dfd3] shadow-lg shadow-[#000000]/5">
                          {message.isLoading ? (
                            <div className="flex items-center gap-3 text-[#554336]">
                              <div className="flex gap-1">
                                <span className="w-2 h-2 bg-[#8f4e00] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                <span className="w-2 h-2 bg-[#8f4e00] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                <span className="w-2 h-2 bg-[#8f4e00] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                              </div>
                              <span className="text-sm font-medium">Analyzing your query...</span>
                            </div>
                          ) : (
                            <div className="space-y-3">
                              <p className="text-base leading-relaxed font-serif whitespace-pre-wrap">{message.content}</p>
                            </div>
                          )}
                        </div>

                        {/* Show Visualization Button */}
                        {!message.isLoading && message.needsVisualization && !showVisualization && (
                          <motion.button
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            onClick={handleShowVisualization}
                            className="mt-3 px-4 py-2 bg-gradient-to-r from-[#8f4e00] to-[#ff9933] text-white text-sm font-medium rounded-xl shadow-lg shadow-[#8f4e00]/20 hover:shadow-[#8f4e00]/30 flex items-center gap-2"
                          >
                            <Sparkles className="w-4 h-4" /> Show Visualization
                          </motion.button>
                        )}
                      </>
                    )}
                  </motion.div>
                ))}
              </div>

              {/* Input Area - Creative Design */}
              <div className="p-4 bg-white border-t border-[#e8d7cb] flex-shrink-0">
                <div className="relative bg-[#faf5ef] rounded-2xl border-2 border-[#f1dfd3] focus-within:border-[#8f4e00] focus-within:ring-4 focus-within:ring-[#8f4e00]/10 transition-all">
                  <textarea
                    ref={inputRef}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="w-full bg-transparent text-[#231a13] text-base font-sans rounded-xl p-4 pr-14 resize-none focus:outline-none placeholder-[#554336]/50"
                    placeholder="Continue the conversation..."
                    rows={2}
                  />
                  <button
                    onClick={() => handleQuery()}
                    disabled={!prompt.trim() || loading}
                    className="absolute right-3 bottom-3 w-10 h-10 bg-gradient-to-r from-[#8f4e00] to-[#a65c00] text-white rounded-xl flex items-center justify-center hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                  </button>
                </div>
                <p className="text-xs text-[#554336]/60 text-center mt-2 font-sans">
                  Press <kbd className="px-1.5 py-0.5 bg-[#f1dfd3] rounded text-[#554336]">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 bg-[#f1dfd3] rounded text-[#554336]">Shift+Enter</kbd> for new line
                </p>
              </div>
            </div>

            {/* Right Panel: Visualization - Only show when needed */}
            {showVisualization && data.length > 0 && (
              <div className="flex-1 bg-[#fdfcfb] flex flex-col h-full border-l border-[#e8d7cb]">
                {/* Panel Header */}
                <div className="p-4 border-b border-[#e8d7cb] flex justify-between items-center bg-white flex-shrink-0">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#8f4e00] to-[#ff9933] flex items-center justify-center text-white">
                      <BarChart3 className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold text-[#231a13] font-serif">
                        {queryPlan?.dataset ? `${queryPlan.dataset.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}` : 'Results'}
                      </h2>
                      <p className="text-xs uppercase tracking-wider text-[#554336]">
                        {queryPlan?.years ? `Census ${queryPlan.years[0]}` : 'Data Visualization'}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={handleDownloadCSV}
                      className="px-4 py-2 bg-[#faf5ef] border border-[#f1dfd3] rounded-xl text-sm font-medium text-[#554336] hover:text-[#8f4e00] hover:border-[#8f4e00] transition-colors flex items-center gap-2"
                    >
                      <Download className="w-4 h-4" /> Export
                    </button>
                    <button className="px-4 py-2 bg-[#faf5ef] border border-[#f1dfd3] rounded-xl text-sm font-medium text-[#554336] hover:text-[#8f4e00] hover:border-[#8f4e00] transition-colors flex items-center gap-2">
                      <Fullscreen className="w-4 h-4" /> Expand
                    </button>
                  </div>
                </div>

                {/* Visualization Content */}
                <div className="flex-1 p-4 overflow-hidden">
                  {/* Tabs */}
                  <div className="flex gap-2 mb-4">
                    <button
                      onClick={() => setActiveTab('table')}
                      className={cn(
                        "px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all",
                        activeTab === 'table'
                          ? "bg-gradient-to-r from-[#8f4e00] to-[#a65c00] text-white shadow-lg"
                          : "bg-white text-[#554336] border border-[#f1dfd3] hover:border-[#8f4e00] hover:text-[#8f4e00]"
                      )}
                    >
                      <TableIcon className="w-4 h-4" /> Table
                    </button>
                    <button
                      onClick={() => setActiveTab('chart')}
                      className={cn(
                        "px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all",
                        activeTab === 'chart'
                          ? "bg-gradient-to-r from-[#8f4e00] to-[#a65c00] text-white shadow-lg"
                          : "bg-white text-[#554336] border border-[#f1dfd3] hover:border-[#8f4e00] hover:text-[#8f4e00]"
                      )}
                    >
                      <BarChart3 className="w-4 h-4" /> Chart
                    </button>
                    <button
                      onClick={() => setActiveTab('map')}
                      className={cn(
                        "px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all",
                        activeTab === 'map'
                          ? "bg-gradient-to-r from-[#8f4e00] to-[#a65c00] text-white shadow-lg"
                          : "bg-white text-[#554336] border border-[#f1dfd3] hover:border-[#8f4e00] hover:text-[#8f4e00]"
                      )}
                    >
                      <MapIcon className="w-4 h-4" /> Map
                    </button>
                  </div>

                  {/* Content */}
                  <div className="h-[calc(100%-70px)] bg-white rounded-2xl border-2 border-[#f1dfd3] overflow-hidden shadow-lg">
                    {activeTab === 'table' && <DataTable data={data} />}
                    {activeTab === 'chart' && <DataChart data={data} chartType="bar" />}
                    {activeTab === 'map' && <IndiaMap data={data} metric="total_population" />}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}