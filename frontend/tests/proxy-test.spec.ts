import { test, expect } from "@playwright/test";
import { join } from "path";

const DEMO_CSV_PATH = join(__dirname, "../../examples/demo/demo_manifest.csv");

test("Test proxy upload functionality", async ({ page }) => {
  // Listen for console messages
  page.on("console", (msg) => {
    console.log(`BROWSER: ${msg.text()}`);
  });

  await page.goto("http://localhost:3004");

  // Ensure direct backend mode is OFF (use proxy)
  const directBackendToggle = page.getByTestId("toggle-direct-backend");
  if (await directBackendToggle.isChecked()) {
    await directBackendToggle.uncheck();
  }

  // Upload file
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(DEMO_CSV_PATH);

  console.log("📁 File uploaded, checking status...");
  await expect(page.getByTestId("upload-status")).toBeVisible();

  // Click submit
  const submitButton = page.getByTestId("run-pipeline");
  await submitButton.click();

  console.log("🚀 Submit clicked, waiting for response...");

  // Wait for processing
  await page.waitForTimeout(10000); // 10 seconds

  // Check final status
  const finalStatus = await page.getByTestId("upload-status").textContent();
  console.log("🏁 Final status:", finalStatus);

  // Check for any errors
  const errorElements = await page.locator(".text-red-600").count();
  if (errorElements > 0) {
    const errorText = await page.locator(".text-red-600").textContent();
    console.log("❌ Error found:", errorText);
  } else {
    console.log("✅ No errors detected");
  }

  // Check for results
  const resultsVisible = await page
    .locator('[data-testid="result-summary"]')
    .isVisible();
  console.log("📊 Results visible:", resultsVisible);
});
