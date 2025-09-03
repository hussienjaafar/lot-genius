import { test, expect } from "@playwright/test";
import path from "path";

test.describe("Live: Basic Upload & Analysis", () => {
  test("CSV upload -> pipeline -> results within 30s", async ({ page }) => {
    const t0 = Date.now();
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /Lot Genius/i }),
    ).toBeVisible();

    const csvPath = path.resolve(
      __dirname,
      "../../realistic_liquidation_manifest.csv",
    );
    await page.getByTestId("file-input").setInputFiles(csvPath);
    await expect(page.getByTestId("upload-status")).toContainText(
      /File selected:/,
    );

    await page
      .getByTestId("optimizer-json")
      .fill(JSON.stringify({ roi_target: 1.25, risk_threshold: 0.8 }));

    await page.getByTestId("run-pipeline").click();

    const summary = page.getByTestId("result-summary");
    await expect(summary).toBeVisible({ timeout: 60_000 });

    await expect(summary).toContainText(/Optimal Bid/i);
    await expect(summary).toContainText(/Expected ROI/i);
    await expect(summary).toContainText(/Meets Constraints/i);

    const elapsedMs = Date.now() - t0;
    test
      .info()
      .annotations.push({
        type: "perf",
        description: `elapsed_ms=${elapsedMs}`,
      });
    expect(elapsedMs).toBeLessThan(30_000);
  });
});
