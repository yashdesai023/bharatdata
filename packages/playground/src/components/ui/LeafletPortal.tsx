"use client";

import { MapContainer, GeoJSON, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useEffect } from 'react';
import L from 'leaflet';
import { formatIndianNumber } from '../../lib/utils';

interface LeafletPortalProps {
  id: string;
  geoData: any;
  stateData: any;
  dataMap: Map<string, number>;
  getColor: (value: number | undefined) => string;
}

function MapControls({ geoData, dataMap }: { geoData: any, dataMap: Map<string, number> }) {
  const map = useMap();

  useEffect(() => {
    if (!geoData || dataMap.size === 0) return;

    // Find all layers that have data and calculate the combined bounds
    const bounds = L.latLngBounds([]);
    let hasMatchingFeatures = false;

    geoData.features.forEach((feature: any) => {
      const stateName = (feature.properties.NAME_1 || feature.properties.ST_NM || "").toLowerCase().trim();
      const distName = (feature.properties.NAME_2 || feature.properties.DISTRICT || feature.properties.dist_name || "").toLowerCase().trim();
      
      if (dataMap.has(stateName) || dataMap.has(distName)) {
        // Precise bounds calculation
        const layer = L.geoJSON(feature);
        bounds.extend(layer.getBounds());
        hasMatchingFeatures = true;
      }
    });

    if (hasMatchingFeatures) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 7, animate: true });
    }
  }, [geoData, dataMap, map]);

  return null;
}

export function LeafletPortal({ id, geoData, stateData, dataMap, getColor }: LeafletPortalProps) {
  // Normalized matching logic to match IndiaMap's root-cause fix
  const normalizeName = (name: string): string => {
    return (name || "")
      .toLowerCase()
      .trim()
      .replace(/\s(commissionerates?|commissionarates?|collectorate|distt?|district|city|urban|rural|railway|rly|hq|headquarters|commr\.?|s\.?p\.?\soffice|pol\.|police)(\s.*)?$/i, '')
      .replace(/[.,]/g, '')
      .trim();
  };

  const getFeatureName = (feature: any) => {
    return (
      feature.properties.NAME_2 || 
      feature.properties.DISTRICT || 
      feature.properties.NAME_1 || 
      "Unknown"
    );
  };

  const style = (feature: any) => {
    const stateName = normalizeName(feature.properties.NAME_1 || feature.properties.ST_NM);
    const distName = normalizeName(feature.properties.NAME_2 || feature.properties.DISTRICT || feature.properties.dist_name);
    const value = dataMap.get(stateName) || dataMap.get(distName);

    return {
      fillColor: getColor(value),
      weight: value !== undefined ? 1.5 : 0.5,
      opacity: 1,
      color: value !== undefined ? '#fff' : '#CBD5E1',
      fillOpacity: value !== undefined ? 1 : 0.1,
    };
  };

  const stateStyle = {
    fillColor: 'transparent',
    weight: 2,
    opacity: 0.8,
    color: '#334155', // Slate-700 for clear state boundaries
    fillOpacity: 0
  };

  const onEachFeature = (feature: any, layer: any) => {
    const rawName = getFeatureName(feature);
    const name = normalizeName(rawName);
    const value = dataMap.get(name);
    
    layer.on({
      mouseover: (e: any) => {
        const l = e.target;
        l.setStyle({
          weight: 2.5,
          color: '#1A365D',
          fillOpacity: 1,
        });
        l.bringToFront();
      },
      mouseout: (e: any) => {
        const l = e.target;
        l.setStyle(style(feature));
      }
    });

    layer.bindTooltip(
      `<div class="p-4 font-body min-w-[140px] shadow-none">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></div>
          <strong class="text-primary block uppercase tracking-widest text-[9px] font-bold">${rawName} Registry</strong>
        </div>
        <div class="space-y-0.5">
          <span class="text-2xl font-semibold text-on-surface-variant font-headline tracking-tighter">
            ${value !== undefined ? formatIndianNumber(value) : '—'}
          </span>
          <span class="text-[9px] text-on-surface-variant/40 block uppercase tracking-widest font-bold">Total Reported Records</span>
        </div>
      </div>`,
      { sticky: true, className: 'leaflet-custom-tooltip border-none shadow-2xl rounded-2xl p-0 overflow-hidden' }
    );
  };

  useEffect(() => {
    return () => {
      // Explicit manual cleanup of the Leaflet instance from the container
      // This prevents the "Map container is already initialized" error during Strict Mode remounts
      const container = L.DomUtil.get(id);
      if (container !== null) {
        // @ts-ignore - _leaflet_id is an internal property
        container._leaflet_id = null;
      }
    };
  }, [id]);

  return (
    <div className="h-full w-full cursor-grab active:cursor-grabbing">
      <MapContainer 
        key={id}
        id={id}
        center={[22.3511, 78.6677]} 
        zoom={4.5} 
        scrollWheelZoom={true}
        className="h-full w-full"
        dragging={true}
        doubleClickZoom={true}
        zoomControl={true}
      >
        <MapControls geoData={geoData} dataMap={dataMap} />
        {geoData && (
          <GeoJSON 
            data={geoData} 
            style={style} 
            onEachFeature={onEachFeature}
          />
        )}
        {stateData && (
          <GeoJSON 
            data={stateData}
            style={stateStyle}
            interactive={false}
          />
        )}
      </MapContainer>
    </div>
  );
}
