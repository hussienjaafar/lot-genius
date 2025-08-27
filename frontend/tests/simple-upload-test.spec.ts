import { test, expect } from "@playwright/test";
import { join } from "path";

const DEMO_CSV_PATH = join(__dirname, "../../examples/demo/demo_manifest.csv");

test("Simple file upload test", async ({ page }) => {
  await page.goto("/");

  // Now only one H1 should exist
  await expect(page.locator("h1")).toHaveCount(1);
  await expect(page.locator("h1")).toHaveText("Lot Genius");

  // Button should be disabled initially
  const submitButton = page.getByTestId("run-pipeline");
  await expect(submitButton).toBeDisabled();

  // Upload the demo CSV file
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(DEMO_CSV_PATH);

  // Button should now be enabled
  await expect(submitButton).toBeEnabled();
  await expect(submitButton).toHaveText("Optimize Lot");

  console.log("✅ File upload working correctly!");
});
