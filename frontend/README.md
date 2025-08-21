# Lot Genius Frontend

Minimal web UI for Lot Genius B-Stock analysis and optimization.

## Setup

**Requirements**: Node.js ≥18

```bash
npm install

cp .env.local.example .env.local
# Put your real values (server-only):
# BACKEND_URL=http://localhost:8787
# LOTGENIUS_API_KEY=your_api_key_here

# In a separate terminal:
uvicorn backend.app.main:app --host 0.0.0.0 --port 8787

# Start Next.js dev server:
npm run dev
```

## Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Production

Build for production:

```bash
npm run build
npm run start
```

## Environment Variables

- `BACKEND_URL`: Backend API URL (default: http://localhost:8787)
- `LOTGENIUS_API_KEY`: API key for backend authentication (server-only)

**Important**: Never prefix API keys with `NEXT_PUBLIC_` as they would be exposed to the client.

## Tech Stack

- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS
- React 18

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx      # Root layout
│   ├── page.tsx        # Main page
│   └── api/           # Server-side API routes
├── lib/
│   └── proxy.ts       # SSE proxy helper
├── styles/
│   └── globals.css    # Global styles with Tailwind
├── .env.local         # Local environment (not committed)
└── .env.local.example # Environment template
```

### Step 12b — Server proxy for streaming

Server-only route proxies multipart uploads to FastAPI and pipes Server-Sent Events (SSE) straight back.

**Env (server-only):**

```
BACKEND_URL=http://localhost:8787
LOTGENIUS_API_KEY=your-key-here
```

**Run:**

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8787
cd frontend && npm i && npm run dev
```

**Manual test via proxy:**

```bash
curl -N \
  -F items_csv=@backend/data/samples/minimal.csv \
  -F opt_json_inline='{"bid":100}' \
  http://localhost:3000/api/pipeline/upload/stream
```

Expect SSE frames: start → parse → validate → enrich_keepa → price → sell → optimize → render_report → done.
CSV-only should return the same 400 JSON as FastAPI.

## Optional

Add to `package.json`:

```json
"engines": { "node": ">=18" }
```

> UI wiring lands in Step 12c (form + live SSE log).

**Heartbeat + slow simulation (for testing only):**

```bash
curl -N \
  -F items_csv=@backend/data/samples/minimal.csv \
  -F opt_json_inline='{"bid": 100}' \
  "http://localhost:3000/api/pipeline/upload/stream?hb=2&slow_ms=5000"
# -> expect periodic 'event: ping' frames while the simulated delay runs
```

**Oversize guard (set small limit just for a local test):**

```bash
# Terminal 1
export MAX_UPLOAD_BYTES=1024
uvicorn backend.app.main:app --host 0.0.0.0 --port 8787
# Terminal 2
dd if=/dev/zero bs=2048 count=1 of=/tmp/big.csv
curl -s -o - -w "\nHTTP %{http_code}\n" -N \
  -F items_csv=@/tmp/big.csv \
  -F opt_json_inline='{"bid": 100}' \
  http://localhost:3000/api/pipeline/upload/stream
# -> HTTP 413 with JSON error

## Configuration knobs

### Backend (FastAPI)
- `MAX_UPLOAD_BYTES` — hard server-side cap on CSV uploads. Default: `10485760` (10 MiB).
- `HEARTBEAT_SEC` — heartbeat interval for SSE `event: ping` when idle. Default: `15`.

### Frontend (Next.js, UI-only)
- `NEXT_PUBLIC_MAX_UPLOAD_MB` — build-time UI guard for file size. Default: `20`.
  This does **not** replace the backend cap; it only shows a friendly error before uploading.

### Behavior notes
- The client uses an `AbortController` to cancel an in-flight stream if you submit a new run.
- The UI shows "Still working…" and counts `ping` heartbeats while the backend is busy.
```
