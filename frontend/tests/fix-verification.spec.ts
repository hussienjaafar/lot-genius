import { test, expect } from "@playwright/test";
import { join } from "path";

const DEMO_CSV_PATH = join(__dirname, "../../examples/demo/demo_manifest.csv");

test("Verify CSV upload fix", async ({ page }) => {
  await page.goto("http://localhost:3002");

  console.log("=== Testing CSV Upload Fix ===");

  // Initial state
  const submitButton = page.getByTestId("run-pipeline");
  await expect(submitButton).toBeDisabled();
  console.log("✅ Button initially disabled");

  // Upload file
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(DEMO_CSV_PATH);
  console.log("📁 File uploaded");

  // Button should be enabled
  await expect(submitButton).toBeEnabled();
  console.log("✅ Button enabled after file upload");

  // Try submitting
  await submitButton.click();
  console.log("🚀 Submit button clicked");

  // Should NOT show "Please choose a CSV" error
  await page.waitForTimeout(2000);

  const errorText = await page
    .locator(".text-red-600")
    .textContent()
    .catch(() => null);
  if (errorText && errorText.includes("Please choose a CSV")) {
    console.log('❌ Still getting "Please choose a CSV" error');
    throw new Error("Fix failed - still getting file selection error");
  } else {
    console.log('✅ No "Please choose a CSV" error - fix successful!');
  }

  // Should show either processing state or different error
  const isProcessing = await submitButton.textContent();
  console.log("Button state after submit:", isProcessing);
});
