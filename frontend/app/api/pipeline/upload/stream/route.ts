import { NextResponse } from "next/server";
import { forwardMultipartSSE } from "../../../../../lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Server misconfigured: missing ${name}`);
  return v;
}

export async function POST(req: Request) {
  console.log("🚀 Proxy route POST called");
  try {
    const BACKEND_URL = requireEnv("BACKEND_URL");
    const LOTGENIUS_API_KEY = requireEnv("LOTGENIUS_API_KEY");
    console.log(`🔄 Proxy: Forwarding to ${BACKEND_URL}`);

    const ct = (req.headers.get("content-type") || "").toLowerCase();
    console.log(`📋 Content-Type: ${ct}`);

    if (!ct.startsWith("multipart/form-data")) {
      console.log(`❌ Invalid content-type: ${ct}`);
      return NextResponse.json(
        {
          error:
            "Expected multipart/form-data with items_csv and optional opt_json or opt_json_inline.",
        },
        { status: 400 },
      );
    }

    const target = new URL(
      "/v1/pipeline/upload/stream",
      BACKEND_URL,
    ).toString();
    console.log(`🎯 Target URL: ${target}`);

    console.log("📤 Calling forwardMultipartSSE...");
    const result = await forwardMultipartSSE(req, target, {
      "X-API-Key": LOTGENIUS_API_KEY,
      Accept: "text/event-stream",
    });
    console.log("✅ forwardMultipartSSE completed");
    return result;
  } catch (err: any) {
    console.error("❌ Proxy error:", err);
    return NextResponse.json(
      { error: err?.message ?? "Proxy error" },
      { status: 500 },
    );
  }
}

export async function GET() {
  return NextResponse.json({ error: "Method Not Allowed" }, { status: 405 });
}
