import { NextRequest } from "next/server";

// Mock SSE API route for testing
export async function POST(req: NextRequest) {
  const searchParams = req.nextUrl.searchParams;
  const heartbeatSeconds = parseInt(searchParams.get("hb") || "10");

  // Create readable stream for SSE
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();

      // Helper function to send SSE event
      const sendEvent = (event: string, data: any) => {
        const eventData =
          typeof data === "string" ? data : JSON.stringify(data);
        const sseData = `event: ${event}\ndata: ${eventData}\n\n`;
        controller.enqueue(encoder.encode(sseData));
      };

      // Helper function to wait
      const wait = (ms: number) =>
        new Promise((resolve) => setTimeout(resolve, ms));

      try {
        // Start the mock pipeline phases in the expected order:
        // start → parse → validate → enrich_keepa → price → sell → evidence → optimize → render_report → done

        // Phase 1: Start
        await wait(500);
        sendEvent("start", {
          phase: "start",
          message: "Pipeline initialization started",
        });

        // Phase 2: Parse
        await wait(1000);
        sendEvent("parse", {
          phase: "parse",
          message: "Parsing CSV file and extracting items",
        });

        // Phase 3: Validate
        await wait(800);
        sendEvent("validate", {
          phase: "validate",
          message: "Validating item data and applying gating policies",
        });

        // Phase 4: Enrich Keepa
        await wait(2000);
        sendEvent("enrich_keepa", {
          phase: "enrich_keepa",
          message: "Enriching items with Keepa price history",
        });

        // Send periodic heartbeat/ping during longer phases
        const heartbeatInterval = setInterval(() => {
          sendEvent("ping", {
            ts: new Date().toISOString(),
            message: "Pipeline heartbeat",
          });
        }, heartbeatSeconds * 1000);

        // Phase 5: Price
        await wait(1500);
        sendEvent("price", {
          phase: "price",
          message: "Estimating current market prices",
        });

        // Phase 6: Sell
        await wait(1200);
        sendEvent("sell", {
          phase: "sell",
          message: "Calculating sell-through probabilities",
        });

        // Phase 7: Evidence (critical for test - must come between sell and optimize)
        await wait(800);
        sendEvent("evidence", {
          phase: "evidence",
          message: "Generating pricing evidence and market analysis",
        });

        // Phase 8: Optimize
        await wait(1000);
        sendEvent("optimize", {
          phase: "optimize",
          message: "Running optimization algorithms",
        });

        // Phase 9: Render Report
        await wait(600);
        sendEvent("render_report", {
          phase: "render_report",
          message: "Generating final report",
        });

        // Clear heartbeat interval
        clearInterval(heartbeatInterval);

        // Final phase: Done with results
        await wait(300);
        sendEvent("done", {
          type: "final_summary",
          payload: {
            bid: 247.5,
            roi_p50: 1.32,
            prob_roi_ge_target: 0.85,
            cash_60d_p50: 425.3,
            core_items_count: 18,
            items: 18,
            meets_constraints: true,
            pipeline_complete: true,
            // Mock report path for demo
            markdown_path:
              "C:/Users/Husse/lot-genius/reports/lot_analysis_20240126_143022.md",
            // Product confidence samples for demo
            confidence_samples: [0.65, 0.82, 0.74, 0.91, 0.58, 0.87],
            // Cache performance metrics for demo
            cache_stats: {
              keepa_cache: {
                hits: 120,
                misses: 25,
                stores: 25,
                evictions: 0,
                hit_ratio: 0.828,
                total_operations: 145,
              },
              ebay_cache: {
                hits: 45,
                misses: 8,
                stores: 8,
                evictions: 0,
                hit_ratio: 0.849,
                total_operations: 53,
              },
            },
          },
        });

        // Close the stream
        controller.close();
      } catch (error) {
        // Send error event
        sendEvent("error", {
          phase: "error",
          message: `Pipeline error: ${error}`,
        });
        controller.close();
      }
    },
  });

  // Return streaming response with proper headers
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-store, max-age=0",
      Connection: "keep-alive",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}

export async function OPTIONS() {
  return new Response(null, {
    status: 200,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}
