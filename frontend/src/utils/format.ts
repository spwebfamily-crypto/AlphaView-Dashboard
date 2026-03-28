function normalizeCurrency(currency: string | null | undefined) {
  return (currency ?? "USD").toUpperCase();
}

export function formatCurrency(value: number | null | undefined, currency?: string | null) {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  const normalizedCurrency = normalizeCurrency(currency);
  const locale = normalizedCurrency === "EUR" ? "pt-PT" : "en-US";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: normalizedCurrency,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatPercent(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return `${value.toFixed(2)}%`;
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  return value.replace("T", " ").slice(0, 16);
}
