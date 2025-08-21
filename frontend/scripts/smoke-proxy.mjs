#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const FRONTEND_URL = process.env.FRONTEND_URL || "http://localhost:3000";

function generateCSV() {
  const content = `title,brand,quantity,est_cost_per_unit
Test Item ${crypto.randomUUID().slice(0, 8)},TestBrand,5,10.50`;
  const tempDir = process.env.TEMP || "/tmp";
  const csvPath = path.join(tempDir, `test-${Date.now()}.csv`);
  fs.writeFileSync(csvPath, content);
  return csvPath;
}

async function smokeFrontendProxy() {
  console.log("🔬 Frontend proxy smoke test");

  const csvPath = generateCSV();
  const formData = new FormData();
  formData.append(
    "items_csv",
    new Blob([fs.readFileSync(csvPath)], { type: "text/csv" }),
    "test.csv",
  );
  formData.append(
    "opt_json_inline",
    JSON.stringify({ bid: 100, roi_target: 1.25 }),
  );

  try {
    const response = await fetch(`${FRONTEND_URL}/api/pipeline/upload/stream`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      console.error(`❌ HTTP ${response.status}`);
      process.exit(1);
    }

    console.log("✅ Connected to stream");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let eventCount = 0;
    let finalReceived = false;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const events = chunk.split("\n\n").filter((e) => e.trim());

      for (const event of events) {
        const dataLine = event
          .split("\n")
          .find((line) => line.startsWith("data: "));
        if (dataLine) {
          try {
            const data = JSON.parse(dataLine.slice(6));
            eventCount++;
            console.log(
              `📡 Event ${eventCount}: ${data.event || data.type || "unknown"}`,
            );

            if (data.type === "final_summary") {
              finalReceived = true;
              console.log("🎯 Final summary:", JSON.stringify(data));
            }
          } catch (e) {
            console.log("📡 Raw event:", dataLine);
          }
        }
      }
    }

    if (finalReceived) {
      console.log("✅ Smoke test passed - received final_summary");
    } else {
      console.error("❌ No final_summary received");
      process.exit(1);
    }
  } catch (error) {
    console.error("❌ Smoke test failed:", error.message);
    process.exit(1);
  } finally {
    fs.unlinkSync(csvPath);
  }
}

smokeFrontendProxy();
