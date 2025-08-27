import { test, expect } from "@playwright/test";
import { join } from "path";

const DEMO_CSV_PATH = join(__dirname, "../../examples/demo/demo_manifest.csv");

test("Visual debug - check button styling", async ({ page }) => {
  await page.goto("http://localhost:3002");

  const submitButton = page.getByTestId("run-pipeline");

  // Check initial button styles
  console.log("=== INITIAL BUTTON STATE ===");
  const initialDisabled = await submitButton.isDisabled();
  const initialClasses = await submitButton.getAttribute("class");
  const initialOpacity = await submitButton.evaluate(
    (el) => getComputedStyle(el).opacity,
  );
  const initialCursor = await submitButton.evaluate(
    (el) => getComputedStyle(el).cursor,
  );
  const initialBgColor = await submitButton.evaluate(
    (el) => getComputedStyle(el).backgroundColor,
  );

  console.log("Disabled:", initialDisabled);
  console.log("Classes:", initialClasses);
  console.log("Opacity:", initialOpacity);
  console.log("Cursor:", initialCursor);
  console.log("Background Color:", initialBgColor);

  // Upload file
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(DEMO_CSV_PATH);
  await page.waitForTimeout(1000);

  // Check button styles after upload
  console.log("=== AFTER FILE UPLOAD ===");
  const afterDisabled = await submitButton.isDisabled();
  const afterClasses = await submitButton.getAttribute("class");
  const afterOpacity = await submitButton.evaluate(
    (el) => getComputedStyle(el).opacity,
  );
  const afterCursor = await submitButton.evaluate(
    (el) => getComputedStyle(el).cursor,
  );
  const afterBgColor = await submitButton.evaluate(
    (el) => getComputedStyle(el).backgroundColor,
  );

  console.log("Disabled:", afterDisabled);
  console.log("Classes:", afterClasses);
  console.log("Opacity:", afterOpacity);
  console.log("Cursor:", afterCursor);
  console.log("Background Color:", afterBgColor);

  // Check if there's a visible difference
  console.log("=== COMPARISON ===");
  console.log("Disabled changed:", initialDisabled !== afterDisabled);
  console.log("Classes changed:", initialClasses !== afterClasses);
  console.log("Opacity changed:", initialOpacity !== afterOpacity);
  console.log("Background color changed:", initialBgColor !== afterBgColor);
});
