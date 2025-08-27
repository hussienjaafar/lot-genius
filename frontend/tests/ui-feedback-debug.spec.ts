import { test, expect } from "@playwright/test";
import { join } from "path";

const DEMO_CSV_PATH = join(__dirname, "../../examples/demo/demo_manifest.csv");

test("Debug UI feedback after submit", async ({ page }) => {
  // Listen for console messages
  page.on("console", (msg) => {
    console.log(`BROWSER ${msg.type().toUpperCase()}:`, msg.text());
  });

  // Listen for network requests
  page.on("response", (response) => {
    if (response.url().includes("/stream")) {
      console.log(
        `NETWORK: ${response.request().method()} ${response.url()} - ${response.status()}`,
      );
    }
  });

  await page.goto("http://localhost:3003");

  // Upload file
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(DEMO_CSV_PATH);
  console.log("📁 File uploaded");

  // Click submit
  const submitButton = page.getByTestId("run-pipeline");
  await expect(submitButton).toBeEnabled();
  console.log("🚀 Clicking submit button...");

  await submitButton.click();

  // Wait for processing and check what happens
  console.log("⏳ Waiting for UI changes...");
  await page.waitForTimeout(5000); // 5 seconds

  // Check button state
  const buttonText = await submitButton.textContent();
  const buttonDisabled = await submitButton.isDisabled();
  console.log("Button text after submit:", buttonText);
  console.log("Button disabled after submit:", buttonDisabled);

  // Check for any error messages
  const errorElements = await page.locator(".text-red-600, .bg-red-50").count();
  console.log("Error elements found:", errorElements);

  if (errorElements > 0) {
    const errorText = await page.locator(".text-red-600").first().textContent();
    console.log("Error message:", errorText);
  }

  // Check for any success/result elements
  const resultElements = await page
    .locator('[data-testid="result-summary"], .text-green-600, .bg-green-50')
    .count();
  console.log("Result elements found:", resultElements);

  // Check for any loading indicators
  const loadingElements = await page
    .locator(".opacity-50, [aria-live], .animate-spin")
    .count();
  console.log("Loading elements found:", loadingElements);

  // Look for any SSE-related elements
  const sseElements = await page
    .locator('[data-testid*="sse"], [data-testid*="console"]')
    .count();
  console.log("SSE elements found:", sseElements);

  // Check the log state
  const logContent = await page.evaluate(() => {
    const logElements = document.querySelectorAll(
      'pre, .font-mono, [data-testid*="log"]',
    );
    return Array.from(logElements)
      .map((el) => el.textContent)
      .join("\n");
  });

  if (logContent) {
    console.log("Log content found:", logContent.substring(0, 200) + "...");
  } else {
    console.log("No log content found");
  }

  console.log("🔍 Debug complete");
});
