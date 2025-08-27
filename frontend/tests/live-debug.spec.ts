import { test, expect } from "@playwright/test";
import { join } from "path";

const DEMO_CSV_PATH = join(__dirname, "../../examples/demo/demo_manifest.csv");

test("Live debug - check actual app behavior", async ({ page }) => {
  // Navigate to your live app
  await page.goto("http://localhost:3002");

  // Take a screenshot first
  await page.screenshot({ path: "debug-initial-state.png" });
  console.log("📸 Screenshot taken: debug-initial-state.png");

  // Check page title and H1
  const title = await page.title();
  console.log("Page title:", title);

  const h1Count = await page.locator("h1").count();
  console.log("H1 count:", h1Count);

  if (h1Count > 0) {
    const h1Text = await page.locator("h1").first().textContent();
    console.log("H1 text:", h1Text);
  }

  // Check if file input exists
  const fileInputExists = await page.locator('input[type="file"]').isVisible();
  console.log("File input visible:", fileInputExists);

  // Check upload area
  const uploadAreaExists = await page.locator(".border-dashed").isVisible();
  console.log("Upload area visible:", uploadAreaExists);

  // Check button state
  const submitButton = page.getByTestId("run-pipeline");
  const buttonExists = await submitButton.isVisible();
  console.log("Submit button visible:", buttonExists);

  if (buttonExists) {
    const buttonDisabled = await submitButton.isDisabled();
    const buttonText = await submitButton.textContent();
    console.log("Button disabled:", buttonDisabled);
    console.log("Button text:", buttonText);
  }

  // Try to upload file
  console.log("Attempting to upload file...");
  const fileInput = page.locator('input[type="file"]');

  try {
    await fileInput.setInputFiles(DEMO_CSV_PATH);
    console.log("✅ File upload command executed");

    // Wait a moment
    await page.waitForTimeout(2000);

    // Check button state again
    const buttonDisabledAfter = await submitButton.isDisabled();
    const buttonTextAfter = await submitButton.textContent();
    console.log("Button disabled after upload:", buttonDisabledAfter);
    console.log("Button text after upload:", buttonTextAfter);

    // Take another screenshot
    await page.screenshot({ path: "debug-after-upload.png" });
    console.log("📸 Screenshot taken: debug-after-upload.png");
  } catch (error) {
    console.log("❌ File upload failed:", error.message);
  }

  // Check for any JavaScript errors
  const logs = await page.evaluate(() => {
    return console.log;
  });
  console.log("Console logs available");
});
