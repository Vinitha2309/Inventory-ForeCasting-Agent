export interface SKU {
  sku_id: string;
  name: string;
  category: string;
  baseline_daily_demand: number;
  seasonality: string;
  volatility: string;
  lead_time_days: number;
  unit_cost: number;
  current_stock: number;
  external_signal: string | null;
}

export interface Report {
  sku_id: string;
  urgency: "watch" | "order-soon" | "critical";
  days_of_cover: number;
  reorder_point: number;
  suggested_qty: number;
  estimated_cost: number;
  confidence: "high" | "medium" | "low";
  reasoning: string;
  generated_by: "llm" | "fallback";
}

export interface ForecastPoint {
  day: number;
  forecast: number;
  upper: number;
  lower: number;
}

export interface Forecast {
  sku_id: string;
  mean_daily_demand: number;
  std_dev: number;
  coefficient_of_variation: number;
  confidence: "high" | "medium" | "low";
  daily_trend: number;
  points: ForecastPoint[];
}

export interface SalesRecord {
  sku_id: string;
  day: number;
  units_sold: number;
}

export interface SkuListItem {
  sku: SKU;
  report: Report;
}

export interface SkuDetail {
  sku: SKU;
  history: SalesRecord[];
  forecast: Forecast;
  report: Report;
}

// In production (e.g. Render static site), set VITE_API_URL to your deployed
// backend's full URL (e.g. https://stockwatch-backend.onrender.com/api).
// Locally, this falls back to the relative "/api" path, which Vite proxies
// to localhost:8000 (see vite.config.ts).
const BASE = import.meta.env.VITE_API_URL || "/api";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listSkus: (): Promise<SkuListItem[]> =>
    fetch(`${BASE}/skus`).then((r) => handle<SkuListItem[]>(r)),

  getSkuDetail: (skuId: string): Promise<SkuDetail> =>
    fetch(`${BASE}/skus/${skuId}`).then((r) => handle<SkuDetail>(r)),

  createSku: (sku: SKU): Promise<SkuListItem> =>
    fetch(`${BASE}/skus`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sku),
    }).then((r) => handle<SkuListItem>(r)),

  refreshReport: (skuId: string): Promise<Report> =>
    fetch(`${BASE}/skus/${skuId}/refresh`, { method: "POST" }).then((r) => handle<Report>(r)),
};
