export async function postJson<T>(path: string, body: any): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

export async function optimize(
  itemsCsvPath: string,
  optJson: object,
): Promise<any> {
  // For now, use the existing pipeline endpoint
  // In a full implementation, this would call a direct optimize endpoint
  const formData = new FormData();

  // This is a simplified version - in reality we'd need to handle file uploads differently
  // For now, we'll return a mock response to demonstrate the UI
  return {
    bid: 150.5,
    roi_p50: 1.45,
    prob_roi_ge_target: 0.78,
    cash_60d_p50: 425.3,
    items: 12,
    meets_constraints: true,
  };
}

export interface SseEvent {
  ts: string;
  stage: string;
  message?: string | object;
}

interface StreamReportOptions {
  useDirectBackend?: boolean;
  forceMock?: boolean;
}

export async function streamReport(
  formData: FormData,
  onEvent: (event: SseEvent) => void,
  options: StreamReportOptions = {},
): Promise<void> {
  const { useDirectBackend = false, forceMock = false } = options;
  // URL selection precedence:
  // 1. If forceMock === true → use mock route
  // 2. Else if NEXT_PUBLIC_USE_MOCK === '1' → use mock route
  // 3. Else if useDirectBackend === true → use direct backend
  // 4. Else → use Next.js proxy
  const useMockApi = process.env.NEXT_PUBLIC_USE_MOCK === "1";

  const url = forceMock
    ? "/api/mock/pipeline/upload/stream?hb=15"
    : useMockApi
      ? "/api/mock/pipeline/upload/stream?hb=15"
      : useDirectBackend
        ? `${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8787"}/v1/pipeline/upload/stream?hb=15`
        : "/api/pipeline/upload/stream?hb=15";

  if (process.env.NODE_ENV === "development") {
    console.log(
      "streamReport: forceMock =",
      forceMock,
      "useMockApi =",
      useMockApi,
      "useDirectBackend =",
      useDirectBackend,
    );
    console.log("streamReport: calling URL =", url);
  }

  const headers: Record<string, string> = {};
  if (useDirectBackend && process.env.NEXT_PUBLIC_API_KEY && !useMockApi) {
    headers["X-API-Key"] = process.env.NEXT_PUBLIC_API_KEY;
  }

  console.log("🚀 Making fetch request to:", url);
  console.log("📋 Headers:", headers);
  console.log(
    "📦 FormData entries:",
    Array.from(formData.entries()).map(([k, v]) => [
      k,
      typeof v === "string" ? v : `File: ${v.name} (${v.size} bytes)`,
    ]),
  );

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: formData,
  });

  console.log("📥 Response received:", response.status, response.statusText);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      // Parse SSE frames (event + data)
      const frames = buffer.split("\n\n");
      for (let i = 0; i < frames.length - 1; i++) {
        const lines = frames[i].split("\n");
        const eventLine = lines.find((l) => l.startsWith("event: "));
        const dataLine = lines.find((l) => l.startsWith("data: "));

        if (eventLine && dataLine) {
          const stage = eventLine.slice(7).trim();

          try {
            const data = JSON.parse(dataLine.slice(6));

            // DEBUG: Log raw SSE data to see exact format
            if (stage === "done") {
              console.log(
                "🔍 RAW SSE DONE EVENT:",
                JSON.stringify(data, null, 2),
              );
            }

            // Extract message from different data formats
            let message: string | object = "";
            if (typeof data === "string") {
              message = data;
            } else if (data.message) {
              message = data.message;
            } else if (data.detail) {
              // Backend error messages use "detail" field
              message = data.detail;
            } else if (data.phase) {
              message = data.phase;
            } else if (data.type === "final_summary") {
              // Pass the entire data object for final summary
              message = data;
            } else if (stage === "done" && data.summary) {
              // Backend sends results in 'summary' field, not 'type: final_summary'
              console.log("🔧 Transforming summary to final_summary format");
              message = { type: "final_summary", payload: data.summary };
            }

            onEvent({
              ts: new Date().toISOString(),
              stage,
              message,
            });
          } catch (e) {
            // If JSON parsing fails, use raw data as message
            onEvent({
              ts: new Date().toISOString(),
              stage,
              message: dataLine.slice(6),
            });
          }
        }
      }
      buffer = frames[frames.length - 1];
    }
  } finally {
    reader.releaseLock();
  }
}

// Utility function for file reading
export function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

// Simple CSV parser (handles basic CSV without quoted commas)
export function parseSimpleCSV(text: string): Record<string, string>[] {
  const lines = text.trim().split("\n");
  if (lines.length < 2) return [];

  const headers = lines[0].split(",").map((h) => h.trim());
  const rows: Record<string, string>[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(",").map((v) => v.trim());
    const row: Record<string, string> = {};

    headers.forEach((header, index) => {
      row[header] = values[index] || "";
    });

    rows.push(row);
  }

  return rows;
}

// JSONL parser
export function parseJSONL(text: string): any[] {
  const lines = text.trim().split("\n");
  const records: any[] = [];

  for (const line of lines) {
    if (line.trim()) {
      try {
        records.push(JSON.parse(line));
      } catch (e) {
        console.warn("Failed to parse JSONL line:", line);
      }
    }
  }

  return records;
}
