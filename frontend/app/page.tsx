"use client";

import { useRef, useState, useEffect } from "react";

type FinalPayload = Record<string, any>;

export default function Home() {
  const csvRef = useRef<HTMLInputElement | null>(null);
  const jsonRef = useRef<HTMLTextAreaElement | null>(null);
  const [log, setLog] = useState<string>("");
  const [final, setFinal] = useState<FinalPayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ctrl, setCtrl] = useState<AbortController | null>(null);
  const [pingCount, setPingCount] = useState(0);
  const [lastPingTs, setLastPingTs] = useState<number | null>(null);
  const [nowTs, setNowTs] = useState<number>(Date.now());
  const [hasCsv, setHasCsv] = useState(false);

  // Build-time configurable UI-only size limit (MB). Not a secret.
  const MAX_UPLOAD_MB = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB ?? "20");
  const MAX_UPLOAD_BYTES_UI = Math.max(1, MAX_UPLOAD_MB) * 1024 * 1024;

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
    setBusy(true);
    setPingCount(0);
    setLastPingTs(null);
    try {
      const ac = new AbortController();
      setCtrl(ac);
      const form = new FormData();
      const csv = csvRef.current?.files?.[0];
      if (!csv) {
        setErr("Please choose a CSV.");
        setBusy(false);
        return;
      }
      // reflect selected CSV
      setHasCsv(true);
      // Client-side size guard (UI only; backend still enforces MAX_UPLOAD_BYTES)
      if (csv.size > MAX_UPLOAD_BYTES_UI) {
        setErr(
          `File too large: ${(csv.size / 1_000_000).toFixed(1)} MB. Max ${MAX_UPLOAD_MB} MB.`,
        );
        setBusy(false);
        return;
      }
      form.append("items_csv", csv);
      const inline = jsonRef.current?.value?.trim();
      if (inline) form.append("opt_json_inline", inline);

      const res = await fetch("/api/pipeline/upload/stream?hb=15", {
        method: "POST",
        body: form,
        signal: ac.signal,
      });
      if (!res.ok) {
        const t = await res.text();
        setErr(`HTTP ${res.status}: ${t}`);
        setBusy(false);
        return;
      }
      const reader = res.body!.getReader();
      const dec = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = dec.decode(value, { stream: true });
        setLog((prev) => prev + chunk);
        buf += chunk;
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
              if (obj?.type === "final_summary") setFinal(obj.payload);
            } catch {}
          }
        }
        buf = frames[frames.length - 1];
      }
    } catch (e: any) {
      setErr(e?.message ?? "Request failed");
    } finally {
      setBusy(false);
      setCtrl(null);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-6">
      <h1 className="text-2xl font-semibold mb-4">Lot Genius — Pipeline</h1>
      <form onSubmit={onSubmit} className="space-y-4 border rounded-2xl p-4">
        <div>
          <label className="block text-sm font-medium">Items CSV</label>
          <input
            ref={csvRef}
            type="file"
            accept=".csv"
            onChange={(e) => {
              const picked = !!e.currentTarget.files?.length;
              setHasCsv(picked);
              if (picked) setErr(null);
            }}
            className="mt-1 block w-full border rounded p-2"
          />
          <p className="mt-1 text-xs text-gray-500">
            Max upload: {MAX_UPLOAD_MB} MB (UI limit)
          </p>
        </div>
        <div>
          <label className="block text-sm font-medium">
            Inline Optimizer JSON (optional)
          </label>
          <textarea
            ref={jsonRef}
            rows={6}
            placeholder='{"bid": 100, "roi_target": 1.25, "risk_threshold": 0.80}'
            className="mt-1 block w-full border rounded p-2 font-mono text-sm"
          />
        </div>
        <button
          disabled={busy || !hasCsv}
          className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
          title={!hasCsv ? "Choose a CSV to enable Run" : undefined}
          aria-disabled={busy || !hasCsv}
        >
          {busy ? "Running…" : "Run Pipeline"}
        </button>
      </form>

      {err && <p className="mt-4 text-red-600 whitespace-pre-wrap">{err}</p>}

      <section className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border rounded-2xl p-4">
          <h2 className="font-semibold mb-2">Progress (SSE)</h2>
          {busy && (
            <div className="mb-2 text-xs text-gray-600" aria-live="polite">
              Still working…{" "}
              {pingCount > 0 && (
                <span>
                  (pings: {pingCount}
                  {lastPingAgo !== null
                    ? ` — last ping ${lastPingAgo}s ago`
                    : ""}
                  )
                </span>
              )}
            </div>
          )}
          <pre className="text-xs whitespace-pre-wrap">{log}</pre>
        </div>

        <div className="border rounded-2xl p-4">
          <h2 className="font-semibold mb-2">Result Summary</h2>
          {!final ? (
            <p className="text-sm text-gray-500">Awaiting final payload…</p>
          ) : (
            <ul className="text-sm space-y-1">
              {Object.entries(final).map(([k, v]) => (
                <li key={k}>
                  <b>{k}:</b> {typeof v === "number" ? v.toFixed(2) : String(v)}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}
