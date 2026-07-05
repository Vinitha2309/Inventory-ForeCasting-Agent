import { useState, type FormEvent } from "react";
import { api } from "./api";
import type { SkuListItem } from "./api";

const initialForm = {
  sku_id: "",
  name: "",
  category: "",
  baseline_daily_demand: "",
  seasonality: "flat",
  volatility: "low",
  lead_time_days: "",
  unit_cost: "",
  current_stock: "",
  external_signal: "",
};

type FormState = typeof initialForm;

type AddProductFormProps = {
  onCreated: (item: SkuListItem) => void;
  onCancel: () => void;
  setError: (message: string | null) => void;
};

export default function AddProductForm({ onCreated, onCancel, setError }: AddProductFormProps) {
  const [form, setForm] = useState<FormState>(initialForm);
  const [submitting, setSubmitting] = useState(false);

  const updateField = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const payload = {
        sku_id: form.sku_id.trim(),
        name: form.name.trim(),
        category: form.category.trim(),
        baseline_daily_demand: Number(form.baseline_daily_demand),
        seasonality: form.seasonality,
        volatility: form.volatility,
        lead_time_days: Number(form.lead_time_days),
        unit_cost: Number(form.unit_cost),
        current_stock: Number(form.current_stock),
        external_signal: form.external_signal.trim() || null,
      };

      const created = await api.createSku(payload);
      onCreated(created);
      setForm(initialForm);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to add product";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <div className="page-header">
        <div>
          <div className="page-title">Add Product</div>
          <div className="page-subtitle">Create a new SKU and generate the first reorder report.</div>
        </div>
      </div>
      <form className="product-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label>
            SKU ID
            <input
              value={form.sku_id}
              onChange={(e) => updateField("sku_id", e.target.value)}
              required
            />
          </label>
          <label>
            Name
            <input
              value={form.name}
              onChange={(e) => updateField("name", e.target.value)}
              required
            />
          </label>
          <label>
            Category
            <input
              value={form.category}
              onChange={(e) => updateField("category", e.target.value)}
              required
            />
          </label>
          <label>
            Baseline Daily Demand
            <input
              type="number"
              min="0"
              step="0.1"
              value={form.baseline_daily_demand}
              onChange={(e) => updateField("baseline_daily_demand", e.target.value)}
              required
            />
          </label>
          <label>
            Lead Time Days
            <input
              type="number"
              min="1"
              value={form.lead_time_days}
              onChange={(e) => updateField("lead_time_days", e.target.value)}
              required
            />
          </label>
          <label>
            Unit Cost
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.unit_cost}
              onChange={(e) => updateField("unit_cost", e.target.value)}
              required
            />
          </label>
          <label>
            Current Stock
            <input
              type="number"
              min="0"
              value={form.current_stock}
              onChange={(e) => updateField("current_stock", e.target.value)}
              required
            />
          </label>
          <label>
            Seasonality
            <select
              value={form.seasonality}
              onChange={(e) => updateField("seasonality", e.target.value)}
            >
              <option value="flat">Flat</option>
              <option value="summer">Summer</option>
              <option value="spring">Spring</option>
              <option value="weather-reactive">Weather-reactive</option>
            </select>
          </label>
          <label>
            Volatility
            <select
              value={form.volatility}
              onChange={(e) => updateField("volatility", e.target.value)}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="extreme">Extreme</option>
            </select>
          </label>
          <label>
            External Signal
            <input
              value={form.external_signal}
              onChange={(e) => updateField("external_signal", e.target.value)}
              placeholder="storm, heatwave, etc."
            />
          </label>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? "Adding product…" : "Add product"}
          </button>
          <button type="button" className="btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
