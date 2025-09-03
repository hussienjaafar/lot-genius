export async function forwardMultipartSSE(
  req: Request,
  targetUrl: string,
  injectHeaders: Record<string, string> = {},
): Promise<Response> {
  console.log("🔧 forwardMultipartSSE starting...");
  console.log(`🎯 Target: ${targetUrl}`);

  // Preserve boundary: forward only content-type + injected headers
  const fwdHeaders = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) fwdHeaders.set("content-type", contentType);
  for (const [k, v] of Object.entries(injectHeaders)) fwdHeaders.set(k, v);
  if (!fwdHeaders.has("accept")) fwdHeaders.set("accept", "text/event-stream");

  console.log("📋 Forward headers:", Object.fromEntries(fwdHeaders.entries()));

  console.log("📡 Making fetch request...");
  const upstream = await fetch(targetUrl, {
    method: "POST",
    headers: fwdHeaders,
    body: req.body as any, // DO NOT rebuild FormData; preserves multipart boundary
    // Node runtime streaming uploads
    // @ts-ignore - duplex is valid in Node.js runtime
    duplex: "half",
  });

  console.log(
    `📥 Upstream response: ${upstream.status} ${upstream.statusText}`,
  );

  // Mirror upstream but add SSE-friendly defaults if omitted
  const outHeaders = new Headers();
  outHeaders.set(
    "content-type",
    upstream.headers.get("content-type") ?? "text/event-stream; charset=utf-8",
  );
  outHeaders.set(
    "cache-control",
    upstream.headers.get("cache-control") ?? "no-cache, no-transform",
  );
  outHeaders.delete("content-length");
  outHeaders.delete("transfer-encoding");

  console.log("📤 Returning response...");
  return new Response(upstream.body, {
    status: upstream.status,
    headers: outHeaders,
  });
}
