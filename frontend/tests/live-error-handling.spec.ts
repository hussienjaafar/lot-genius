import { test, expect } from "@playwright/test";

test.describe("Live: Error handling scenarios", () => {
  test("rejects when no file provided", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("run-pipeline").click();
    await expect(page.getByText(/Please choose a CSV\./)).toBeVisible();
  });

  test("UI shows error for malformed JSON", async ({ page }) => {
    await page.goto("/");
    // Attach a tiny CSV via new File to bypass file requirement
    const handle = page.getByTestId("file-input");
    await handle.setInputFiles({
      name: "mini.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("sku,price\nA,10"),
    });
    // Fill malformed JSON
    await page.getByTestId("optimizer-json").fill("{ this is not json }");
    await page.getByTestId("run-pipeline").click();
    // Expect visible error text
    await expect(page.getByText(/HTTP \d{3}|Request failed/i)).toBeVisible({
      timeout: 60000,
    });
  });
});
