import { test, expect } from "@playwright/test";
import { join } from "path";

const DEMO_CSV_PATH = join(__dirname, "../../examples/demo/demo_manifest.csv");

test("Debug stream content and response", async ({ page }) => {
  // Capture all logs
  page.on("console", (msg) => {
    console.log(`BROWSER: ${msg.text()}`);
  });

  await page.goto("http://localhost:3004");

  // Upload file
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(DEMO_CSV_PATH);

  // Click submit
  const submitButton = page.getByTestId("run-pipeline");
  await submitButton.click();

  // Wait for completion and check what we got
  await page.waitForTimeout(10000); // 10 seconds

  // Check for any results on page
  console.log("=== CHECKING PAGE CONTENT ===");

  // Check if results section appeared
  const resultSection = page.locator('[data-testid="result-summary"]');
  const hasResults = await resultSection.isVisible();
  console.log("Results section visible:", hasResults);

  // Check for any text containing numbers or metrics
  const pageText = await page.textContent("body");
  const hasNumbers = /\$\d+|\d+%|\d+\.\d+/.test(pageText || "");
  console.log("Page contains numeric results:", hasNumbers);

  // Check for any error messages
  const errorElements = await page.locator(".text-red-600").count();
  console.log("Error elements found:", errorElements);

  if (errorElements > 0) {
    const errorText = await page.locator(".text-red-600").first().textContent();
    console.log("Error message:", errorText);
  }

  // Look for log content that might contain the raw response
  const logElements = await page.locator("pre, .font-mono").count();
  console.log("Log elements found:", logElements);

  if (logElements > 0) {
    const logText = await page.locator("pre, .font-mono").first().textContent();
    console.log("Log content preview:", logText?.substring(0, 200) + "...");
  }

  console.log("=== DEBUG COMPLETE ===");
});
