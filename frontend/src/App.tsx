import { useEffect, useState } from "react";
import AddProductForm from "./AddProductForm";
import type { Report, SkuDetail } from "./api";
import {
  ResponsiveContainer,
  LineChart,
  BarChart,
  Line,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

const API_URL = import.meta.env.VITE_API_URL || "/api";

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">Day {label}</div>
      {payload.map((entry: any) => {
        const labelMap: Record<string, string> = {
          daysOfCover: "Days of cover",
          suggestedQty: "Suggested Qty",
          Sales: "Sales",
          Forecast: "Forecast",
          Inventory: "Inventory",
        };
        const name = entry.name || labelMap[entry.dataKey] || entry.dataKey;
        return (
          <div key={entry.dataKey} className="chart-tooltip-item" style={{ color: entry.color }}>
            {name}: {entry.value}
          </div>
        );
      })}
    </div>
  );
}

function WrappedTick({ x, y, payload, maxChars = 12, center = false }: any) {
  const text: string = String(payload.value || "");
  const words = text.split(" ");
  const lines: string[] = [];
  let current = "";
  for (const w of words) {
    if ((current + " " + w).trim().length <= maxChars) {
      current = (current + " " + w).trim();
    } else {
      if (current) lines.push(current);
      current = w;
    }
  }
  if (current) lines.push(current);
  const textAnchor = center ? "middle" : "end";
  const textY = center ? 14 : 0;

  return (
    <g transform={`translate(${x}, ${y})`}>
      <text x={0} y={textY} textAnchor={textAnchor} fontSize={10} fill="#374151">
        {lines.map((line, i) => (
          <tspan key={i} x={0} dy={i === 0 ? "0" : "12"}>
            {line}
          </tspan>
        ))}
      </text>
    </g>
  );
}
