import { test, expect } from "@playwright/test";
import { join } from "path";

const DEMO_CSV_PATH = join(__dirname, "../../examples/demo/demo_manifest.csv");

test("Debug file selection mechanism", async ({ page }) => {
  await page.goto("http://localhost:3002");

  // Add console logging to track what's happening
  await page.addInitScript(() => {
    // Override the file input change handler to see what's happening
    window.addEventListener("load", () => {
      const fileInput = document.querySelector('input[type="file"]');
      if (fileInput) {
        console.log("🔍 File input found, adding debug listeners");

        fileInput.addEventListener("change", (e) => {
          console.log("📁 File input change event fired");
          console.log("📁 Files selected:", e.target.files?.length || 0);
          if (e.target.files?.length > 0) {
            console.log("📁 File name:", e.target.files[0].name);
            console.log("📁 File type:", e.target.files[0].type);
            console.log("📁 File size:", e.target.files[0].size);
          }
        });

        // Check if the onFiles callback is being called
        const originalOnFiles = window.handleCsvFiles;
        if (originalOnFiles) {
          window.handleCsvFiles = function (...args) {
            console.log("✅ handleCsvFiles called with:", args);
            return originalOnFiles.apply(this, args);
          };
        }
      }
    });
  });

  // Listen for console messages
  page.on("console", (msg) => {
    console.log("BROWSER:", msg.text());
  });

  await page.waitForLoadState("networkidle");

  // Check initial state
  const submitButton = page.getByTestId("run-pipeline");
  console.log("Initial button disabled:", await submitButton.isDisabled());

  // Try uploading file
  console.log("Attempting file upload...");
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(DEMO_CSV_PATH);

  await page.waitForTimeout(2000);

  // Check final state
  console.log("Final button disabled:", await submitButton.isDisabled());

  // Try clicking the button to see the error
  console.log("Clicking submit button...");
  await submitButton.click();

  await page.waitForTimeout(2000);

  // Check for error messages
  const errorElement = page.locator(".text-red-600, .bg-red-50");
  if (await errorElement.isVisible()) {
    const errorText = await errorElement.textContent();
    console.log("Error message displayed:", errorText);
  }
});
