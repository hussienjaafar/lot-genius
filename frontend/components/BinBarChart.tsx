import React from "react";

interface BinData {
  label: string;
  count: number;
  pred: number;
  actual: number;
  bias: number;
}

interface BinBarChartProps {
  bins: BinData[];
  width?: number;
  height?: number;
  className?: string;
}

export default function BinBarChart({
  bins,
  width = 400,
  height = 200,
  className = "",
}: BinBarChartProps) {
  if (!bins.length) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-50 border rounded ${className}`}
        style={{ width, height }}
      >
        <span className="text-sm text-gray-500">No calibration data</span>
      </div>
    );
  }

  const maxCount = Math.max(...bins.map((b) => b.count));
  const maxBias = Math.max(...bins.map((b) => Math.abs(b.bias)));

  const margin = { top: 20, right: 20, bottom: 40, left: 40 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;

  const barWidth = (chartWidth / bins.length) * 0.8;
  const barSpacing = chartWidth / bins.length;

  return (
    <div className={className}>
      <svg width={width} height={height} className="border rounded bg-white">
        {/* Chart area */}
        <g transform={`translate(${margin.left}, ${margin.top})`}>
          {/* Y-axis */}
          <line
            x1={0}
            y1={0}
            x2={0}
            y2={chartHeight}
            stroke="#e5e7eb"
            strokeWidth={1}
          />

          {/* X-axis */}
          <line
            x1={0}
            y1={chartHeight}
            x2={chartWidth}
            y2={chartHeight}
            stroke="#e5e7eb"
            strokeWidth={1}
          />

          {/* Bars */}
          {bins.map((bin, i) => {
            const barHeight = (bin.count / maxCount) * chartHeight;
            const x = i * barSpacing + (barSpacing - barWidth) / 2;
            const y = chartHeight - barHeight;

            // Bias indicator
            const biasIntensity = Math.abs(bin.bias) / maxBias;
            const biasColor =
              bin.bias > 0
                ? `rgba(239, 68, 68, ${biasIntensity})`
                : `rgba(34, 197, 94, ${biasIntensity})`;

            return (
              <g key={bin.label}>
                {/* Main bar */}
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barHeight}
                  fill="rgb(59, 130, 246)"
                  stroke="rgb(37, 99, 235)"
                  strokeWidth={1}
                />

                {/* Bias overlay */}
                {bin.bias !== 0 && (
                  <rect
                    x={x}
                    y={y}
                    width={barWidth}
                    height={barHeight}
                    fill={biasColor}
                    opacity={0.6}
                  />
                )}

                {/* Count label */}
                {bin.count > 0 && (
                  <text
                    x={x + barWidth / 2}
                    y={y - 5}
                    textAnchor="middle"
                    fontSize={10}
                    fill="#374151"
                  >
                    {bin.count}
                  </text>
                )}

                {/* X-axis label */}
                <text
                  x={x + barWidth / 2}
                  y={chartHeight + 15}
                  textAnchor="middle"
                  fontSize={10}
                  fill="#6b7280"
                >
                  {bin.label}
                </text>
              </g>
            );
          })}

          {/* Y-axis labels */}
          <text x={-10} y={5} textAnchor="end" fontSize={10} fill="#6b7280">
            {maxCount}
          </text>
          <text
            x={-10}
            y={chartHeight + 5}
            textAnchor="end"
            fontSize={10}
            fill="#6b7280"
          >
            0
          </text>
        </g>

        {/* Chart title */}
        <text
          x={width / 2}
          y={15}
          textAnchor="middle"
          fontSize={12}
          fontWeight="600"
          fill="#374151"
        >
          Calibration Bins (Count)
        </text>

        {/* Y-axis title */}
        <text
          x={15}
          y={height / 2}
          textAnchor="middle"
          fontSize={10}
          fill="#6b7280"
          transform={`rotate(-90, 15, ${height / 2})`}
        >
          Samples
        </text>
      </svg>

      {/* Legend */}
      <div className="flex gap-4 mt-2 text-xs text-gray-600 justify-center">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-blue-500 rounded"></div>
          <span>Count</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-red-400 rounded opacity-60"></div>
          <span>Over-confident</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-green-400 rounded opacity-60"></div>
          <span>Under-confident</span>
        </div>
      </div>
    </div>
  );
}
