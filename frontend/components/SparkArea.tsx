import React from "react";

interface SparkAreaProps {
  series: number[];
  width?: number;
  height?: number;
  className?: string;
}

export default function SparkArea({
  series,
  width = 200,
  height = 40,
  className = "",
}: SparkAreaProps) {
  if (!series.length) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 rounded ${className}`}
        style={{ width, height }}
      >
        <span className="text-xs text-gray-500">No data</span>
      </div>
    );
  }

  const minValue = Math.min(...series);
  const maxValue = Math.max(...series);
  const range = maxValue - minValue || 1; // Avoid division by zero

  const points = series
    .map((value, index) => {
      const x = (index / (series.length - 1)) * width;
      const y = height - ((value - minValue) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  const pathData = `M 0,${height} L ${points} L ${width},${height} Z`;

  return (
    <svg
      width={width}
      height={height}
      className={`overflow-hidden ${className}`}
      viewBox={`0 0 ${width} ${height}`}
    >
      <path
        d={pathData}
        fill="rgba(59, 130, 246, 0.2)"
        stroke="rgb(59, 130, 246)"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
