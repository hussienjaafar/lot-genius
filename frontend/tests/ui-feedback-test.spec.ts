import { test, expect } from "@playwright/test";
import { join } from "path";

const DEMO_CSV_PATH = join(__dirname, "../../examples/demo/demo_manifest.csv");

test("Test comprehensive UI feedback", async ({ page }) => {
  // Listen for console logs
  page.on("console", (msg) => {
    console.log(`BROWSER: ${msg.text()}`);
  });

  await page.goto("http://localhost:3004");

  console.log("=== Testing File Upload Feedback ===");

  // Initial state - no upload status
  await expect(page.getByTestId("upload-status")).not.toBeVisible();
  console.log("✅ No upload status initially");

  // Upload file
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(DEMO_CSV_PATH);

  // Should show file selected status
  await expect(page.getByTestId("upload-status")).toBeVisible();
  const uploadStatus = await page.getByTestId("upload-status").textContent();
  console.log("📄 Upload status:", uploadStatus);

  expect(uploadStatus).toContain("File selected:");
  expect(uploadStatus).toContain("demo_manifest.csv");

  // Button should be enabled
  const submitButton = page.getByTestId("run-pipeline");
  await expect(submitButton).toBeEnabled();
  console.log("✅ Button enabled after file selection");

  // Click submit
  console.log("🚀 Clicking submit...");
  await submitButton.click();

  // Should show processing status
  await page.waitForTimeout(1000);
  const processingStatus = await page
    .getByTestId("upload-status")
    .textContent();
  console.log("⚙️ Processing status:", processingStatus);

  // Wait for completion
  await page.waitForTimeout(5000);
  const finalStatus = await page.getByTestId("upload-status").textContent();
  console.log("🏁 Final status:", finalStatus);
});
