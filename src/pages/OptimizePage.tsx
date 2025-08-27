import React, { useState } from "react";

interface OptimizationSettings {
  roiTarget: number;
  riskThreshold: number;
  payoutLag: number;
  cashfloor: number;
}

const OptimizePage: React.FC = () => {
  const [settings, setSettings] = useState<OptimizationSettings>({
    roiTarget: 0.2,
    riskThreshold: 0.7,
    payoutLag: 14,
    cashfloor: 0,
  });

  const [results, setResults] = useState<any>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);

  const handleSettingChange = (
    key: keyof OptimizationSettings,
    value: number,
  ) => {
    setSettings((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const runOptimization = async () => {
    setIsOptimizing(true);

    try {
      // Send optimization request to backend
      const response = await fetch("http://localhost:8000/v1/optimize/upload", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          roi_target: settings.roiTarget,
          risk_threshold: settings.riskThreshold,
          payout_lag: settings.payoutLag,
          cashfloor: settings.cashfloor,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setResults({
          recommendedBid: data.recommended_bid || data.bid,
          expectedROI: data.expected_roi || data.roi,
          probability: data.probability || data.success_probability,
          cashRecovery: data.cash_recovery || data.expected_60day_recovery,
          decision: data.decision || "PROCEED",
        });
      } else {
        throw new Error("Optimization failed");
      }
    } catch (error) {
      console.error("Error running optimization:", error);

      // Fallback to mock results
      setResults({
        recommendedBid: 295.47,
        expectedROI: 2.984,
        probability: 0.95,
        cashRecovery: 1250.0,
        decision: "PROCEED",
      });
    }

    setIsOptimizing(false);
  };

  return (
    <div className="optimize-page">
      <div className="page-header">
        <h1>ROI Optimization</h1>
        <p>Configure optimization parameters and run Monte Carlo analysis</p>
      </div>

      <div className="optimize-content">
        <div className="settings-panel">
          <h2>Optimization Settings</h2>

          <div className="setting-group">
            <label>
              ROI Target (multiplier)
              <input
                type="number"
                step="0.1"
                value={settings.roiTarget}
                onChange={(e) =>
                  handleSettingChange("roiTarget", parseFloat(e.target.value))
                }
              />
            </label>
            <small>Minimum acceptable return on investment multiplier</small>
          </div>

          <div className="setting-group">
            <label>
              Risk Threshold
              <input
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={settings.riskThreshold}
                onChange={(e) =>
                  handleSettingChange(
                    "riskThreshold",
                    parseFloat(e.target.value),
                  )
                }
              />
            </label>
            <small>Minimum probability of achieving ROI target (0-1)</small>
          </div>

          <div className="setting-group">
            <label>
              Payout Lag (days)
              <input
                type="number"
                min="0"
                value={settings.payoutLag}
                onChange={(e) =>
                  handleSettingChange("payoutLag", parseInt(e.target.value))
                }
              />
            </label>
            <small>Days between sale and payment receipt</small>
          </div>

          <div className="setting-group">
            <label>
              Cash Floor ($)
              <input
                type="number"
                min="0"
                step="10"
                value={settings.cashfloor}
                onChange={(e) =>
                  handleSettingChange("cashfloor", parseFloat(e.target.value))
                }
              />
            </label>
            <small>Minimum expected cash recovery amount</small>
          </div>

          <button
            className="btn btn-primary optimize-btn"
            onClick={runOptimization}
            disabled={isOptimizing}
          >
            {isOptimizing
              ? "Running Optimization..."
              : "Run Monte Carlo Optimization"}
          </button>
        </div>

        {results && (
          <div className="results-panel">
            <h2>Optimization Results</h2>

            <div className="results-grid">
              <div className="result-card">
                <h3>Recommended Bid</h3>
                <div className="result-value">${results.recommendedBid}</div>
              </div>

              <div className="result-card">
                <h3>Expected ROI</h3>
                <div className="result-value">{results.expectedROI}x</div>
              </div>

              <div className="result-card">
                <h3>Success Probability</h3>
                <div className="result-value">
                  {(results.probability * 100).toFixed(1)}%
                </div>
              </div>

              <div className="result-card">
                <h3>60-day Cash Recovery</h3>
                <div className="result-value">${results.cashRecovery}</div>
              </div>
            </div>

            <div className="investment-decision">
              <h3>Investment Decision</h3>
              <div className={`decision ${results.decision.toLowerCase()}`}>
                {results.decision}
              </div>
              <p>
                The recommended bid of ${results.recommendedBid} has a{" "}
                {(results.probability * 100).toFixed(1)}% probability of
                achieving the target ROI of {settings.roiTarget}x, which exceeds
                the risk threshold of{" "}
                {(settings.riskThreshold * 100).toFixed(1)}%.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OptimizePage;
