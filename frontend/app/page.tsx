"use client";

import { useRef, useState, useEffect } from "react";
import MetricCard from "../components/MetricCard";
import ProgressBar from "../components/ProgressBar";
import Section from "../components/Section";
import FilePicker from "../components/FilePicker";
import SseConsole from "../components/SseConsole";
import { streamReport, SseEvent } from "../lib/api";

type FinalPayload = Record<string, any>;

export default function Home() {
  const jsonRef = useRef<HTMLTextAreaElement | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [log, setLog] = useState<string>("");
  const [final, setFinal] = useState<FinalPayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ctrl, setCtrl] = useState<AbortController | null>(null);
  const [pingCount, setPingCount] = useState(0);
  const [lastPingTs, setLastPingTs] = useState<number | null>(null);
  const [nowTs, setNowTs] = useState<number>(Date.now());
  const [hasCsv, setHasCsv] = useState(false);
  const [activeTab, setActiveTab] = useState<"optimize" | "sse">("optimize");
  const [sseEvents, setSseEvents] = useState<SseEvent[]>([]);
  const [useDirectBackend, setUseDirectBackend] = useState(false);
  const [forceMock, setForceMock] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Optional fields for optimization
  const [calibrationLogPath, setCalibrationLogPath] = useState("");
  const [outMdPath, setOutMdPath] = useState("");
  const [outHtmlPath, setOutHtmlPath] = useState("");
  const [outPdfPath, setOutPdfPath] = useState("");

  // Build-time configurable UI-only size limit (MB). Not a secret.
  const MAX_UPLOAD_MB = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB ?? "20");
  const MAX_UPLOAD_BYTES_UI = Math.max(1, MAX_UPLOAD_MB) * 1024 * 1024;

  // Mount effect to prevent hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  // Tick every second while busy so "last ping Xs ago" updates in real time
  useEffect(() => {
    if (!busy) return;
    const id = setInterval(() => setNowTs(Date.now()), 1000);
    return () => clearInterval(id);
  }, [busy]);

  const lastPingAgo =
    lastPingTs !== null
      ? Math.max(0, Math.floor((nowTs - lastPingTs) / 1000))
      : null;

  const handleCsvFiles = (files: FileList) => {
    if (files.length > 0) {
      const file = files[0];
      setCsvFile(file);
      setHasCsv(true);
      setErr(null);
      setUploadStatus(
        `File selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`,
      );
      console.log(
        `✅ File selected: ${file.name} (${file.size} bytes, ${file.type})`,
      );
    }
  };

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    // cancel any in-flight request first
    if (ctrl) {
      try {
        ctrl.abort();
      } catch {}
    }
    setLog("");
    setFinal(null);
    setErr(null);
    setUploadStatus("");
    setBusy(true);
    setPingCount(0);
    setLastPingTs(null);
    setSseEvents([]);

    try {
      const ac = new AbortController();
      setCtrl(ac);
      const form = new FormData();
      if (!csvFile) {
        setErr("Please choose a CSV.");
        setBusy(false);
        return;
      }
      console.log(
        `🚀 Starting upload: ${csvFile.name} (${csvFile.size} bytes)`,
      );
      setUploadStatus("Preparing upload...");
      // Client-side size guard (UI only; backend still enforces MAX_UPLOAD_BYTES)
      if (csvFile.size > MAX_UPLOAD_BYTES_UI) {
        setErr(
          `File too large: ${(csvFile.size / 1_000_000).toFixed(1)} MB. Max ${MAX_UPLOAD_MB} MB.`,
        );
        setBusy(false);
        return;
      }
      form.append("items_csv", csvFile);
      console.log(`📤 FormData created with file: ${csvFile.name}`);
      setUploadStatus("Uploading file to server...");
      const inline = jsonRef.current?.value?.trim();
      console.log(`📋 JSON value from textbox: "${inline}"`);
      if (inline) {
        form.append("opt_json_inline", inline);
        console.log(`✅ Added opt_json_inline to FormData`);
      } else {
        console.log(`❌ No JSON value found, opt_json_inline not added`);
      }

      // Add optional paths if provided
      if (calibrationLogPath.trim()) {
        const optObj = inline ? JSON.parse(inline) : {};
        optObj.calibration_log_path = calibrationLogPath.trim();
        form.append("opt_json_inline", JSON.stringify(optObj));
      }

      if (activeTab === "sse") {
        // Add visible instrumentation event for test observation
        setSseEvents((prev) => [
          ...prev,
          {
            ts: new Date().toISOString(),
            stage: "submit",
            message: "Submitting SSE request",
          },
        ]);

        // Use streaming API - ensure streamReport is called exactly once
        await streamReport(
          form,
          (event) => {
            setSseEvents((prev) => [...prev, event]);
            if (event.stage === "ping") {
              setPingCount((n) => n + 1);
              setLastPingTs(Date.now());
            }
            // Handle final results for SSE tab
            if (
              event.stage === "done" &&
              typeof event.message === "object" &&
              event.message &&
              "type" in event.message &&
              (event.message as any).type === "final_summary"
            ) {
              console.log(
                "🎯 Final summary detected for SSE tab:",
                event.message,
              );
              setFinal((event.message as any).payload);
            }
          },
          { useDirectBackend, forceMock },
        );
      } else {
        // Use existing implementation for optimize tab
        const useMockApi = process.env.NEXT_PUBLIC_USE_MOCK === "1";
        const url = useMockApi
          ? "/api/mock/pipeline/upload/stream?hb=15"
          : useDirectBackend
            ? `${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}/v1/optimize/upload/stream?hb=15`
            : "/api/pipeline/upload/stream?hb=15";

        console.log(`🌐 Request URL: ${url}`);

        const headers: Record<string, string> = {};
        if (
          useDirectBackend &&
          process.env.NEXT_PUBLIC_API_KEY &&
          !useMockApi
        ) {
          headers["X-API-Key"] = process.env.NEXT_PUBLIC_API_KEY;
        }

        const res = await fetch(url, {
          method: "POST",
          headers,
          body: form,
          signal: ac.signal,
        });
        console.log(`📡 Response received: ${res.status} ${res.statusText}`);
        if (!res.ok) {
          const t = await res.text();
          console.log(`❌ Error response: ${t}`);
          const errorMsg = `HTTP ${res.status}: ${t}`;
          setErr(errorMsg);
          setUploadStatus(`Upload failed - ${res.status} ${res.statusText}`);
          console.error(`🚨 PERSISTENT ERROR: ${errorMsg}`);
          setBusy(false);
          return;
        }
        setUploadStatus("Upload successful! Processing...");
        const reader = res.body!.getReader();
        const dec = new TextDecoder();
        let buf = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) {
            console.log("📋 Stream reading completed");
            setUploadStatus("Processing completed!");
            break;
          }
          const chunk = dec.decode(value, { stream: true });
          setLog((prev) => prev + chunk);
          buf += chunk;
          console.log(`📊 Received chunk: ${chunk.length} chars`);
          // Parse SSE frames (event + data). We handle 'ping' and the final payload.
          const frames = buf.split("\n\n");
          for (let i = 0; i < frames.length - 1; i++) {
            const lines = frames[i].split("\n");
            const evLine = lines.find((l) => l.startsWith("event: "));
            const dataLine = lines.find((l) => l.startsWith("data: "));
            const evName = evLine ? evLine.slice(7).trim() : "message";
            if (evName === "ping") {
              setPingCount((n) => n + 1);
              setLastPingTs(Date.now());
            }
            if (dataLine) {
              try {
                const obj = JSON.parse(dataLine.slice(6));
                console.log(`📋 Parsed SSE data:`, obj);
                if (obj?.type === "final_summary") {
                  console.log(`🎯 Final summary found:`, obj.payload);
                  setFinal(obj.payload);
                } else {
                  console.log(`📄 Other SSE event: ${obj?.type || "unknown"}`);
                }
              } catch (e) {
                console.log(`❌ Failed to parse SSE data: ${dataLine}`, e);
              }
            }
          }
          buf = frames[frames.length - 1];
        }
      }
    } catch (e: any) {
      console.log(`❌ Request failed: ${e?.message}`);
      setErr(e?.message ?? "Request failed");
      setUploadStatus("Request failed");
    } finally {
      setBusy(false);
      setCtrl(null);
    }
  }

  const renderOptimizeResults = () => {
    if (!final) return null;

    return (
      <div className="mt-6 space-y-6" data-testid="result-summary">
        <Section
          title="Optimization Results"
          description="Summary metrics from the lot optimization"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricCard
              label="Optimal Bid"
              value={
                typeof final.bid === "number"
                  ? `$${final.bid.toFixed(2)}`
                  : final.bid || "N/A"
              }
              hint="Recommended maximum bid amount"
            />
            <MetricCard
              label="Expected ROI"
              value={
                typeof final.roi_p50 === "number"
                  ? `${(final.roi_p50 * 100).toFixed(1)}%`
                  : final.roi_p50 || "N/A"
              }
              hint="50th percentile return on investment"
            />
            <MetricCard
              label="60-Day Cash"
              value={
                typeof final.cash_60d_p50 === "number"
                  ? `$${final.cash_60d_p50.toFixed(2)}`
                  : final.cash_60d_p50 || "N/A"
              }
              hint="Expected cash flow at 60 days"
            />
            <MetricCard
              label="Items Count"
              value={final.core_items_count || final.items || "N/A"}
              hint="Number of items analyzed"
            />
            <MetricCard
              label="Meets Constraints"
              value={final.meets_constraints ? "Yes" : "No"}
              hint="Whether the lot meets risk constraints"
            />
            <div className="md:col-span-1">
              <ProgressBar
                value={final.prob_roi_ge_target || 0}
                label="ROI Target Probability"
                className="mt-4"
              />
            </div>
          </div>

          {/* Product Confidence Section */}
          {final.confidence_samples && final.confidence_samples.length > 0 && (
            <div
              className="mt-6 p-4 bg-green-50 rounded-lg border border-green-200"
              data-testid="confidence-section"
            >
              <h3 className="text-lg font-semibold text-green-800 mb-2">
                Product Confidence
              </h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-green-700">
                    Average Confidence:
                  </span>
                  <span
                    className="font-medium text-green-800"
                    data-testid="confidence-average"
                  >
                    {(
                      final.confidence_samples.reduce(
                        (a: number, b: number) => a + b,
                        0,
                      ) / final.confidence_samples.length
                    ).toFixed(2)}
                  </span>
                </div>
                <div className="text-xs text-green-600">
                  Based on {final.confidence_samples.length} items with product
                  matching data
                </div>
              </div>
            </div>
          )}

          {/* Cache Metrics Section */}
          {final.cache_stats && (
            <div
              className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200"
              data-testid="cache-metrics-section"
            >
              <h3 className="text-lg font-semibold text-blue-800 mb-3">
                Cache Performance
              </h3>
              <div className="space-y-3">
                {Object.entries(final.cache_stats).map(
                  ([cacheName, stats]: [string, any]) => (
                    <div
                      key={cacheName}
                      className="flex items-center justify-between p-2 bg-white rounded border"
                    >
                      <span className="text-sm font-medium text-blue-700 capitalize">
                        {cacheName.replace("_cache", "").replace("_", " ")}{" "}
                        Cache:
                      </span>
                      <div
                        className="text-xs text-blue-600 space-x-3"
                        data-testid={`cache-${cacheName}`}
                      >
                        <span>Hits: {stats.hits || 0}</span>
                        <span>Misses: {stats.misses || 0}</span>
                        <span>
                          Hit Ratio: {((stats.hit_ratio || 0) * 100).toFixed(1)}
                          %
                        </span>
                        <span>Total: {stats.total_operations || 0}</span>
                      </div>
                    </div>
                  ),
                )}
              </div>
            </div>
          )}

          {/* Copy Report Path Button */}
          {final.markdown_path && (
            <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-1">
                    Report Generated
                  </h3>
                  <p className="text-sm text-gray-600">
                    Report saved to: {final.markdown_path}
                  </p>
                </div>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(final.markdown_path);
                    const btn = document.querySelector(
                      '[data-testid="copy-report-path"]',
                    ) as HTMLButtonElement;
                    const originalText = btn?.textContent;
                    if (btn) {
                      btn.textContent = "Copied!";
                      setTimeout(() => {
                        btn.textContent = originalText;
                      }, 2000);
                    }
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
                  data-testid="copy-report-path"
                >
                  Copy Report Path
                </button>
              </div>
            </div>
          )}
        </Section>
      </div>
    );
  };

  return (
    <main className="mx-auto max-w-6xl p-6">
      <h1 className="text-3xl font-bold mb-6">Lot Genius</h1>

      {/* Configuration and Tab Navigation */}
      <div className="mb-6 space-y-4">
        <div className="flex items-center space-x-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={useDirectBackend}
              onChange={(e) => setUseDirectBackend(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              data-testid="toggle-direct-backend"
            />
            <span className="text-blue-700 font-medium">
              Direct Backend Mode
            </span>
          </label>
          <span className="text-xs text-blue-600">
            {mounted && useDirectBackend
              ? `Direct calls to ${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}`
              : "Using Next.js API proxy"}
          </span>
        </div>

        {/* Test-only force mock toggle */}
        {process.env.NEXT_PUBLIC_TEST === "1" && (
          <div className="flex items-center space-x-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
            <label className="flex items-center space-x-2 text-sm">
              <input
                type="checkbox"
                checked={forceMock}
                onChange={(e) => setForceMock(e.target.checked)}
                className="rounded border-gray-300 text-yellow-600 focus:ring-yellow-500"
                data-testid="toggle-force-mock"
              />
              <span className="text-yellow-700 font-medium">
                Force Mock API (Test Mode)
              </span>
            </label>
            <span className="text-xs text-yellow-600">
              {forceMock
                ? "Forcing mock API route for testing"
                : "Normal API routing"}
            </span>
          </div>
        )}

        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setActiveTab("optimize")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === "optimize"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            Optimize Lot
          </button>
          <button
            onClick={() => setActiveTab("sse")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === "sse"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            Pipeline (SSE)
          </button>
        </div>
      </div>

      {/* Optimize Tab */}
      {activeTab === "optimize" && (
        <div>
          <Section
            title="Lot Optimization"
            description="Upload your items CSV and optimization parameters to get bidding recommendations"
          >
            <form onSubmit={onSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <FilePicker
                    label="Items CSV (Required)"
                    accept=".csv"
                    onFiles={handleCsvFiles}
                    data-testid="file-input"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Max upload: {MAX_UPLOAD_MB} MB (UI limit)
                  </p>
                  {uploadStatus && (
                    <div className="mt-2 p-2 bg-blue-50 rounded border border-blue-200">
                      <p
                        className="text-sm text-blue-700 font-medium"
                        data-testid="upload-status"
                      >
                        📄 {uploadStatus}
                      </p>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Optimizer JSON (Optional)
                  </label>
                  <textarea
                    ref={jsonRef}
                    rows={6}
                    placeholder='{"bid": 100, "roi_target": 1.25, "risk_threshold": 0.80}'
                    className="w-full border border-gray-300 rounded-lg p-3 font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    data-testid="optimizer-json"
                  />
                </div>
              </div>

              {/* Optional Output Paths */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Calibration Log Path (Optional)
                  </label>
                  <input
                    type="text"
                    value={calibrationLogPath}
                    onChange={(e) => setCalibrationLogPath(e.target.value)}
                    placeholder="/path/to/calibration.jsonl"
                    className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Markdown Output (Optional)
                  </label>
                  <input
                    type="text"
                    value={outMdPath}
                    onChange={(e) => setOutMdPath(e.target.value)}
                    placeholder="/path/to/report.md"
                    className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <button
                disabled={busy || !csvFile}
                className="px-6 py-3 rounded-lg bg-blue-600 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
                title={
                  !csvFile ? "Choose a CSV to enable optimization" : undefined
                }
                data-testid="run-pipeline"
              >
                {busy ? "Optimizing..." : "Optimize Lot"}
              </button>
            </form>
          </Section>

          {err && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600 whitespace-pre-wrap">{err}</p>
            </div>
          )}

          {renderOptimizeResults()}
        </div>
      )}

      {/* SSE Tab */}
      {activeTab === "sse" && (
        <div>
          <Section
            title="Pipeline Streaming"
            description="Monitor real-time progress of the optimization pipeline"
          >
            <form onSubmit={onSubmit} className="space-y-4">
              <FilePicker
                label="Items CSV (Required)"
                accept=".csv"
                onFiles={handleCsvFiles}
                data-testid="file-input"
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Optimizer JSON (Optional)
                </label>
                <textarea
                  ref={jsonRef}
                  rows={4}
                  defaultValue='{"bid": 100, "roi_target": 1.25, "risk_threshold": 0.80}'
                  className="w-full border border-gray-300 rounded-lg p-3 font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <button
                type="submit"
                disabled={busy || !csvFile}
                className="px-4 py-2 rounded-lg bg-green-600 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-green-700 transition-colors"
                data-testid="run-pipeline"
              >
                {busy ? "Running..." : "Run Pipeline"}
              </button>

              {busy && (
                <div className="text-sm text-gray-600" aria-live="polite">
                  Pipeline running...{" "}
                  {pingCount > 0 && (
                    <span>
                      (pings: {pingCount}
                      {lastPingAgo !== null
                        ? ` (last ping ${lastPingAgo}s ago)`
                        : ""}
                      )
                    </span>
                  )}
                </div>
              )}

              <SseConsole events={sseEvents} newestFirst={false} />
            </form>
          </Section>

          {err && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600 whitespace-pre-wrap">{err}</p>
            </div>
          )}

          {renderOptimizeResults()}
        </div>
      )}
    </main>
  );
}
