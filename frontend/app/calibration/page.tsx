"use client";

import React, { useState } from "react";
import MetricCard from "../../components/MetricCard";
import Section from "../../components/Section";
import FilePicker from "../../components/FilePicker";
import BinBarChart from "../../components/BinBarChart";
import { readFileAsText, parseSimpleCSV, parseJSONL } from "../../lib/api";

interface CalibrationMetrics {
  brierScore: number;
  samples: number;
  priceMetrics?: {
    mae: number;
    rmse: number;
    mape: number;
    samples: number;
  };
  calibrationBins: {
    label: string;
    count: number;
    pred: number;
    actual: number;
    bias: number;
  }[];
}

export default function CalibrationPage() {
  const [predictionsFile, setPredictionsFile] = useState<File | null>(null);
  const [outcomesFile, setOutcomesFile] = useState<File | null>(null);
  const [metrics, setMetrics] = useState<CalibrationMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePredictionsFiles = (files: FileList) => {
    if (files.length > 0) {
      setPredictionsFile(files[0]);
      setError(null);
    }
  };

  const handleOutcomesFiles = (files: FileList) => {
    if (files.length > 0) {
      setOutcomesFile(files[0]);
      setError(null);
    }
  };

  const computeCalibration = async () => {
    if (!predictionsFile || !outcomesFile) {
      setError("Please select both predictions and outcomes files");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Read files
      const predictionsText = await readFileAsText(predictionsFile);
      const outcomesText = await readFileAsText(outcomesFile);

      // Parse files
      const predictions = parseJSONL(predictionsText);
      const outcomes = parseSimpleCSV(outcomesText);

      if (predictions.length === 0) {
        throw new Error("No predictions found in JSONL file");
      }
      if (outcomes.length === 0) {
        throw new Error("No outcomes found in CSV file");
      }

      // Join predictions with outcomes on sku_local
      const joined: any[] = [];
      const outcomesMap = new Map();

      outcomes.forEach((outcome) => {
        if (outcome.sku_local) {
          outcomesMap.set(outcome.sku_local, outcome);
        }
      });

      predictions.forEach((pred) => {
        const outcome = outcomesMap.get(pred.sku_local);
        if (outcome) {
          joined.push({
            ...pred,
            ...outcome,
            realized_price: parseFloat(outcome.realized_price) || 0,
            sold_within_horizon:
              outcome.sold_within_horizon === "True" ||
              outcome.sold_within_horizon === "true" ||
              outcome.sold_within_horizon === "1",
            days_to_sale: parseFloat(outcome.days_to_sale) || 0,
          });
        }
      });

      if (joined.length === 0) {
        throw new Error(
          "No matching records found between predictions and outcomes",
        );
      }

      // Compute calibration metrics
      const calibrationMetrics = computeCalibrationMetrics(joined);
      setMetrics(calibrationMetrics);
    } catch (err: any) {
      setError(err.message || "Failed to compute calibration metrics");
    } finally {
      setLoading(false);
    }
  };

  const computeCalibrationMetrics = (data: any[]): CalibrationMetrics => {
    // Filter data with valid probability predictions
    const probData = data.filter((d) => {
      const prob = d.predicted_sell_p60 ?? d.sell_p60;
      return prob !== undefined && prob !== null && !isNaN(prob);
    });

    if (probData.length === 0) {
      throw new Error("No valid probability predictions found");
    }

    // Compute Brier score
    let brierSum = 0;
    probData.forEach((d) => {
      const predicted = d.predicted_sell_p60 ?? d.sell_p60;
      const actual = d.sold_within_horizon ? 1 : 0;
      brierSum += Math.pow(predicted - actual, 2);
    });
    const brierScore = brierSum / probData.length;

    // Compute calibration bins (0.1 wide)
    const bins = Array.from({ length: 10 }, (_, i) => ({
      label: `${(i * 0.1).toFixed(1)}-${((i + 1) * 0.1).toFixed(1)}`,
      records: [] as any[],
    }));

    probData.forEach((d) => {
      const predicted = d.predicted_sell_p60 ?? d.sell_p60;
      const binIndex = Math.min(9, Math.floor(predicted * 10));
      bins[binIndex].records.push(d);
    });

    const calibrationBins = bins.map((bin) => {
      const count = bin.records.length;
      if (count === 0) {
        return {
          label: bin.label,
          count: 0,
          pred: 0,
          actual: 0,
          bias: 0,
        };
      }

      const predMean =
        bin.records.reduce(
          (sum, d) => sum + (d.predicted_sell_p60 ?? d.sell_p60),
          0,
        ) / count;
      const actualRate =
        bin.records.filter((d) => d.sold_within_horizon).length / count;
      const bias = predMean - actualRate;

      return {
        label: bin.label,
        count,
        pred: predMean,
        actual: actualRate,
        bias,
      };
    });

    // Compute price metrics if available
    const priceData = data.filter((d) => {
      const predPrice = d.predicted_price ?? d.est_price_mu;
      const realPrice = d.realized_price;
      return (
        predPrice !== undefined &&
        predPrice !== null &&
        !isNaN(predPrice) &&
        realPrice !== undefined &&
        realPrice !== null &&
        !isNaN(realPrice) &&
        realPrice > 0
      );
    });

    let priceMetrics;
    if (priceData.length > 0) {
      let maeSum = 0;
      let mapeSum = 0;
      let rmseSum = 0;

      priceData.forEach((d) => {
        const predicted = d.predicted_price ?? d.est_price_mu;
        const actual = d.realized_price;
        const error = Math.abs(predicted - actual);

        maeSum += error;
        mapeSum += (error / actual) * 100;
        rmseSum += Math.pow(predicted - actual, 2);
      });

      priceMetrics = {
        mae: maeSum / priceData.length,
        mape: mapeSum / priceData.length,
        rmse: Math.sqrt(rmseSum / priceData.length),
        samples: priceData.length,
      };
    }

    return {
      brierScore,
      samples: probData.length,
      priceMetrics,
      calibrationBins,
    };
  };

  const downloadMetrics = () => {
    if (!metrics) return;

    const report = {
      timestamp: new Date().toISOString(),
      calibration_metrics: {
        brier_score: metrics.brierScore,
        samples: metrics.samples,
        ...(metrics.priceMetrics && {
          price_metrics: metrics.priceMetrics,
        }),
      },
      calibration_bins: metrics.calibrationBins,
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `calibration-report-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="mx-auto max-w-6xl p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Calibration Analysis</h1>
        <p className="text-gray-600 mt-2">
          Analyze prediction accuracy by comparing model outputs with realized
          outcomes
        </p>
      </div>

      <Section
        title="Input Files"
        description="Upload your prediction logs and outcome data for calibration analysis"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FilePicker
            label="Predictions JSONL"
            accept=".jsonl,.json"
            onFiles={handlePredictionsFiles}
          />
          <FilePicker
            label="Outcomes CSV"
            accept=".csv"
            onFiles={handleOutcomesFiles}
          />
        </div>

        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            <strong>CSV Limitation:</strong> This simple parser expects
            comma-separated values without quoted commas. For complex CSV files
            with quoted fields, please ensure they are properly formatted or
            pre-processed.
          </p>
        </div>

        <div className="mt-6 flex gap-4">
          <button
            onClick={computeCalibration}
            disabled={!predictionsFile || !outcomesFile || loading}
            className="px-6 py-3 rounded-lg bg-blue-600 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
          >
            {loading ? "Computing..." : "Compute Calibration"}
          </button>

          {metrics && (
            <button
              onClick={downloadMetrics}
              className="px-6 py-3 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 transition-colors"
            >
              Download JSON Report
            </button>
          )}
        </div>
      </Section>

      {error && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {metrics && (
        <div className="mt-8 space-y-8">
          <Section
            title="Calibration Metrics"
            description="Overall model calibration performance"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                label="Brier Score"
                value={metrics.brierScore.toFixed(4)}
                hint="Lower is better. Perfect calibration = 0"
              />
              <MetricCard
                label="Probability Samples"
                value={metrics.samples.toLocaleString()}
                hint="Number of records with valid probability predictions"
              />
              {metrics.priceMetrics && (
                <>
                  <MetricCard
                    label="Price MAE"
                    value={`$${metrics.priceMetrics.mae.toFixed(2)}`}
                    hint="Mean Absolute Error for price predictions"
                  />
                  <MetricCard
                    label="Price MAPE"
                    value={`${metrics.priceMetrics.mape.toFixed(1)}%`}
                    hint="Mean Absolute Percentage Error"
                  />
                </>
              )}
            </div>

            {metrics.priceMetrics && (
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                <MetricCard
                  label="Price RMSE"
                  value={`$${metrics.priceMetrics.rmse.toFixed(2)}`}
                  hint="Root Mean Square Error for price predictions"
                />
                <MetricCard
                  label="Price Samples"
                  value={metrics.priceMetrics.samples.toLocaleString()}
                  hint="Number of records with valid price predictions and outcomes"
                />
              </div>
            )}
          </Section>

          <Section
            title="Calibration Bins"
            description="Distribution of predictions vs actual outcomes across probability ranges"
          >
            <BinBarChart
              bins={metrics.calibrationBins}
              width={600}
              height={300}
            />

            <div className="mt-6 overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Range
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Count
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Pred Mean
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actual Rate
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Bias
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {metrics.calibrationBins.map((bin, index) => (
                    <tr
                      key={index}
                      className={bin.count === 0 ? "text-gray-400" : ""}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {bin.label}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {bin.count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {bin.count > 0 ? bin.pred.toFixed(3) : "-"}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {bin.count > 0 ? bin.actual.toFixed(3) : "-"}
                      </td>
                      <td
                        className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                          bin.bias > 0.05
                            ? "text-red-600"
                            : bin.bias < -0.05
                              ? "text-green-600"
                              : "text-gray-500"
                        }`}
                      >
                        {bin.count > 0
                          ? (bin.bias > 0 ? "+" : "") + bin.bias.toFixed(3)
                          : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        </div>
      )}
    </main>
  );
}
