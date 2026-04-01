"use client";

import { useEffect, useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { formatIndianNumber } from '../../lib/utils';
import { Loader2, AlertCircle } from 'lucide-react';

// Single Dynamic Import for the entire Leaflet suite to prevent ChunkLoadErrors
const LeafletPortal = dynamic(
  () => import('./LeafletPortal').then(mod => mod.LeafletPortal),
  { 
    ssr: false, 
    loading: () => (
      <div className="h-full w-full flex items-center justify-center bg-surface-container-low/20 animate-pulse">
        <Loader2 className="w-6 h-6 animate-spin text-primary/20" />
      </div>
    )
  }
);

interface IndiaMapProps {
  data: any[];
  metric?: string;
  category?: string;
  title?: string;
}

const COLOR_STEPS = ["#F8FAFC", "#BAE6FD", "#38BDF8", "#0369A1", "#082F49"]; // Premium Sky/Ocean Palette
const GEO_JSON_SOURCES = [
  "/maps/india_districts.json", // Local high-reliability source
  "https://cdn.jsdelivr.net/gh/Anuj-Nigam/India-GeoJSON@master/India_Districts.json", 
  "https://code.highcharts.com/mapdata/countries/in/in-all.geo.json"
];

export function IndiaMap({ data, metric = "total_cases", category = "entity_name", title }: IndiaMapProps) {
  const [geoData, setGeoData] = useState<any>(null);
  const [stateData, setStateData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isMounted, setIsMounted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Unique ID for this map instance to prevent Leaflet conflicts
  const mapId = useMemo(() => `map-container-${Math.random().toString(36).substr(2, 9)}`, []);

  useEffect(() => {
    setIsMounted(true);
    
    // Fetch both District and State boundaries for high-fidelity rendering
    const fetchMaps = async () => {
      try {
        const [distRes, stateRes] = await Promise.all([
          fetch("/maps/india_districts.json"),
          fetch("/maps/india_states.json")
        ]);
        
        if (!distRes.ok || !stateRes.ok) throw new Error("Local map storage unreachable");
        
        const [distJson, stateJson] = await Promise.all([distRes.json(), stateRes.json()]);
        setGeoData(distJson);
        setStateData(stateJson);
        setLoading(false);
      } catch (err) {
        console.error("Map fetch error:", err);
        setError("Failed to load geographic boundaries.");
        setLoading(false);
      }
    };

    fetchMaps();
    return () => setIsMounted(false);
  }, []);

  // Universal Administrative Normalizer to bridge NCRB labels to Geographic Boundaries
  const normalizeName = (name: string): string => {
    return name
      .toLowerCase()
      .trim()
      // Strip common administrative qualifiers, suffixes, and punctuation
      .replace(/\s(commissionerates?|commissionarates?|collectorate|distt?|district|city|urban|rural|railway|rly|hq|headquarters|commr\.?|s\.?p\.?\soffice|pol\.|police)(\s.*)?$/i, '')
      .replace(/[.,]/g, '')
      .trim();
  };

  const dataMap = useMemo(() => {
    const map = new Map<string, number>();
    
    data.forEach(item => {
      const rawName = String(item[category]);
      const normalizedBase = normalizeName(rawName);
      const val = typeof item[metric] === 'number' ? item[metric] : 0;
      
      // Automatic Multi-Target aggregation for Metro regions (e.g. Mumbai Railway + Mumbai Commr -> Mumbai)
      const targets = [normalizedBase];
      if (normalizedBase === 'mumbai') {
        targets.push('mumbai city', 'mumbai suburban');
      } else if (normalizedBase === 'navi mumbai') {
        targets.push('thane', 'raigad');
      }

      targets.forEach(target => {
        if (map.has(target)) {
          map.set(target, map.get(target)! + val);
        } else {
          map.set(target, val);
        }
      });
    });

    return map;
  }, [data, metric, category]);

  const maxVal = useMemo(() => {
    const vals = Array.from(dataMap.values());
    return vals.length > 0 ? Math.max(...vals) : 1;
  }, [dataMap]);

  const getColor = (value: number | undefined) => {
    if (value === undefined || value === 0) return COLOR_STEPS[0];
    
    // Use Square Root distribution to provide better variance for skewed data (crime counts)
    const ratio = Math.sqrt(value) / Math.sqrt(maxVal);
    const index = Math.min(
      COLOR_STEPS.length - 1,
      Math.floor(ratio * (COLOR_STEPS.length - 1)) + 1
    );
    return COLOR_STEPS[index];
  };

  if (error) {
    return (
      <div className="h-[500px] w-full bg-red-50/10 rounded-2xl flex flex-col items-center justify-center gap-4 border border-red-200/20">
        <AlertCircle className="w-8 h-8 text-red-500/50" />
        <p className="text-red-900/60 font-label text-xs uppercase tracking-widest">{error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="h-[500px] w-full bg-surface-container-low/30 rounded-2xl flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary/30" />
      </div>
    );
  }

  return (
    <div className="space-y-6 font-label animate-in fade-in duration-1000">
      <div className="flex flex-col gap-1 px-4 pt-4">
        <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/60">
          {title || "Geospatial Distribution"}
        </h3>
        <p className="text-[11px] text-on-surface-variant/40 italic">Interactive Choropleth • Unified Chunk Loading</p>
      </div>

      <div className="h-[600px] w-full bg-[#FBF9F5]/40 rounded-2xl overflow-hidden relative z-0">
        {isMounted && !loading && geoData && stateData && (
          <LeafletPortal 
            id={mapId}
            geoData={geoData}
            stateData={stateData}
            dataMap={dataMap}
            getColor={getColor}
          />
        )}

        {/* Legend */}
        <div className="absolute bottom-8 right-8 bg-surface-container-lowest/90 backdrop-blur-md p-6 rounded-2xl shadow-2xl border border-outline-variant/30 z-[1000] space-y-4">
           <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary">Prevalence Tier</h4>
           <div className="flex items-center gap-1.5 h-3">
             {COLOR_STEPS.map((c, i) => (
               <div key={i} className="flex-1 w-8 h-full rounded-sm" style={{ backgroundColor: c }} />
             ))}
           </div>
           <div className="flex justify-between text-[10px] text-on-surface-variant/50 font-bold uppercase tracking-widest">
             <span>Registry Low</span>
             <span>Registry High</span>
           </div>
        </div>
      </div>
    </div>
  );
}
