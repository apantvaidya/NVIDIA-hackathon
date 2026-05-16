export function formatCurrency(value?: number): string {
  return typeof value === "number"
    ? value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 })
    : "n/a";
}

export function formatNumber(value?: number, digits = 0): string {
  return typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: digits }) : "n/a";
}

export function formatPercent(value?: number, digits = 0): string {
  return typeof value === "number" ? `${(value * 100).toFixed(digits)}%` : "n/a";
}

export function titleize(value?: string): string {
  return (value || "unknown").replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}
