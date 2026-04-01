"use client";

import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  LineChart, 
  Line,
  Cell
} from 'recharts';
import { formatIndianNumber } from '../../lib/utils';

interface DataChartProps {
  data: any[];
  type?: 'bar' | 'line' | 'horizontal-bar';
  title?: string;
  metric?: string;
  category?: string;
}

const PRIMARY_COLOR = "#1A365D";
const PALETTE = ["#1a365dff", "#4A5568", "#718096", "#A0AEC0", "#CBD5E0"];

export function DataChart({ data, type = 'bar', title, metric = "total_cases", category = "entity_name" }: DataChartProps) {
  if (!data || data.length === 0) return null;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-surface-container-lowest p-3 shadow-xl border border-outline-variant/30 rounded-lg text-[10px] font-label font-bold uppercase tracking-wider">
          <p className="text-primary mb-1 italic">{label}</p>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            <p className="text-on-surface-variant font-mono font-normal normal-case tracking-normal">
              {formatIndianNumber(payload[0].value)} records
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  const renderChart = () => {
    if (type === 'bar') {
      return (
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" opacity={0.5} />
          <XAxis 
            dataKey={category} 
            axisLine={false} 
            tickLine={false} 
            tick={{ fontSize: 9, fill: "#5C6066", fontWeight: 600, fontFamily: "var(--font-inter)" }} 
            interval={0}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fontSize: 9, fill: "#5C6066", fontWeight: 600, fontFamily: "var(--font-inter)" }} 
            tickFormatter={formatIndianNumber}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#F1F5F9' }} />
          <Bar dataKey={metric} fill={PRIMARY_COLOR} radius={[4, 4, 0, 0]} barSize={32}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} />
            ))}
          </Bar>
        </BarChart>
      );
    }

    if (type === 'line') {
      return (
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" opacity={0.5} />
          <XAxis 
            dataKey={category} 
            axisLine={false} 
            tickLine={false} 
            tick={{ fontSize: 9, fill: "#5C6066", fontWeight: 600, fontFamily: "var(--font-inter)" }} 
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fontSize: 9, fill: "#5C6066", fontWeight: 600, fontFamily: "var(--font-inter)" }} 
            tickFormatter={formatIndianNumber}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line 
            type="monotone" 
            dataKey={metric} 
            stroke={PRIMARY_COLOR} 
            strokeWidth={3} 
            dot={{ r: 4, fill: PRIMARY_COLOR, strokeWidth: 2, stroke: "#fff" }} 
            activeDot={{ r: 6 }}
          />
        </LineChart>
      );
    }

    if (type === 'horizontal-bar') {
      return (
        <BarChart data={data} layout="vertical" margin={{ left: 40 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E2E8F0" opacity={0.5} />
          <XAxis 
            type="number"
            axisLine={false} 
            tickLine={false} 
            tick={{ fontSize: 9, fill: "#5C6066", fontWeight: 600, fontFamily: "var(--font-inter)" }} 
            tickFormatter={formatIndianNumber}
          />
          <YAxis 
            dataKey={category} 
            type="category"
            axisLine={false} 
            tickLine={false} 
            tick={{ fontSize: 9, fill: "#5C6066", fontWeight: 600, fontFamily: "var(--font-inter)" }} 
            width={120}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#F1F5F9' }} />
          <Bar dataKey={metric} fill={PRIMARY_COLOR} radius={[0, 4, 4, 0]} barSize={20}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} />
            ))}
          </Bar>
        </BarChart>
      );
    }

    return null;
  };

  return (
    <div className="space-y-6 font-label animate-in fade-in duration-700 delay-150">
      <div className="flex flex-col gap-1 px-4">
        <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/60 mr-auto">
          {title || "Statistical Visualization"}
        </h3>
        <p className="text-[11px] text-on-surface-variant/40 italic">Aggregated Analysis by BharatData Logic</p>
      </div>

      <div className="h-[400px] w-full bg-surface-container-low/20 rounded-xl p-6">
        <ResponsiveContainer width="100%" height="100%">
          {renderChart() || <></>}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
