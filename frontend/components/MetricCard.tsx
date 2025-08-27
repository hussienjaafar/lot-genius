import React from "react";

interface MetricCardProps {
  label: string;
  value: React.ReactNode;
  hint?: string;
  deltaPct?: number;
}

export default function MetricCard({
  label,
  value,
  hint,
  deltaPct,
}: MetricCardProps) {
  const deltaColor = deltaPct
    ? deltaPct > 0
      ? "text-green-600"
      : deltaPct < 0
        ? "text-red-600"
        : "text-gray-500"
    : "";

  return (
    <div className="border rounded-lg p-4 bg-white">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{label}</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">{value}</p>
          {hint && (
            <p className="text-xs text-gray-500 mt-1" title={hint}>
              {hint}
            </p>
          )}
        </div>
        {deltaPct !== undefined && (
          <div className={`text-sm font-medium ${deltaColor}`}>
            {deltaPct > 0 ? "+" : ""}
            {deltaPct.toFixed(1)}%
          </div>
        )}
      </div>
    </div>
  );
}
