import React from "react";

interface ProgressBarProps {
  value: number; // 0-1
  label?: string;
  className?: string;
}

export default function ProgressBar({
  value,
  label,
  className = "",
}: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, value * 100));
  const displayValue = percentage.toFixed(1);

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <div className="flex justify-between text-sm font-medium text-gray-700 mb-1">
          <span>{label}</span>
          <span>{displayValue}%</span>
        </div>
      )}
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={label || `${displayValue}% complete`}
        />
      </div>
    </div>
  );
}
