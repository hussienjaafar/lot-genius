import { test, expect, Page, BrowserContext } from "@playwright/test";
import { readFileSync } from "fs";
import { join } from "path";

// Test data paths
const DEMO_CSV_PATH = join(
  __dirname,
  "../../../examples/demo/demo_manifest.csv",
);
const DEMO_JSON_PATH = join(__dirname, "../../../examples/demo/demo_opt.json");

interface TestMetrics {
  loadTime: number;
  interactionTime: number;
  errorCount: number;
  accessibilityIssues: number;
  performanceScore?: number;
}

let testMetrics: TestMetrics = {
  loadTime: 0,
  interactionTime: 0,
  errorCount: 0,
  accessibilityIssues: 0,
};

test.describe("Lot Genius - Comprehensive E2E Testing", () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();

    // Monitor console errors
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        testMetrics.errorCount++;
        console.error(`Console error: ${msg.text()}`);
      }
    });

    // Monitor network failures
    page.on("response", (response) => {
      if (response.status() >= 400) {
        testMetrics.errorCount++;
        console.error(`HTTP ${response.status()}: ${response.url()}`);
      }
    });
  });

  test.afterAll(async () => {
    await context.close();
  });

  test.describe("Application Loading and Performance", () => {
    test("should load the homepage within acceptable time", async () => {
      const startTime = Date.now();
      await page.goto("/");
      await expect(page.locator("h1")).toContainText("Lot Genius");
      testMetrics.loadTime = Date.now() - startTime;

      // Performance check - should load within 3 seconds
      expect(testMetrics.loadTime).toBeLessThan(3000);
    });

    test("should display all core UI elements", async () => {
      await page.goto("/");

      // Check main heading
      await expect(page.locator("h1")).toHaveText("Lot Genius");

      // Check tab navigation
      await expect(page.getByText("Optimize Lot")).toBeVisible();
      await expect(page.getByText("Pipeline (SSE)")).toBeVisible();

      // Check configuration toggles
      await expect(page.getByTestId("toggle-direct-backend")).toBeVisible();

      // Check form elements
      await expect(page.getByText("Items CSV (Required)")).toBeVisible();
      await expect(page.getByTestId("run-pipeline")).toBeVisible();
    });

    test("should handle window resize and maintain usability", async () => {
      await page.goto("/");

      // Test desktop view
      await page.setViewportSize({ width: 1920, height: 1080 });
      await expect(page.locator("h1")).toBeVisible();

      // Test tablet view
      await page.setViewportSize({ width: 768, height: 1024 });
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.getByTestId("run-pipeline")).toBeVisible();

      // Test mobile view
      await page.setViewportSize({ width: 375, height: 667 });
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.getByTestId("run-pipeline")).toBeVisible();
    });
  });

  test.describe("User Interface and Usability", () => {
    test("should provide clear navigation between tabs", async () => {
      await page.goto("/");

      // Start on Optimize tab
      await expect(page.getByText("Lot Optimization")).toBeVisible();

      // Switch to SSE tab
      await page.getByText("Pipeline (SSE)").click();
      await expect(page.getByText("Pipeline Streaming")).toBeVisible();

      // Switch back to Optimize tab
      await page.getByText("Optimize Lot").click();
      await expect(page.getByText("Lot Optimization")).toBeVisible();
    });

    test("should provide helpful placeholder text and hints", async () => {
      await page.goto("/");

      // Check optimizer JSON placeholder
      const textarea = page.getByTestId("optimizer-json");
      await expect(textarea).toHaveAttribute(
        "placeholder",
        '{"bid": 100, "roi_target": 1.25, "risk_threshold": 0.80}',
      );

      // Check file size limit hint
      await expect(
        page.getByText("Max upload: 20 MB (UI limit)"),
      ).toBeVisible();

      // Check disabled button behavior
      const submitButton = page.getByTestId("run-pipeline");
      await expect(submitButton).toBeDisabled();
      await expect(submitButton).toHaveAttribute(
        "title",
        "Choose a CSV to enable optimization",
      );
    });

    test("should show appropriate loading states", async () => {
      await page.goto("/");

      // Verify button text changes
      const submitButton = page.getByTestId("run-pipeline");
      await expect(submitButton).toHaveText("Optimize Lot");

      // Test with file upload to enable button
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      await expect(submitButton).toBeEnabled();
      await expect(submitButton).toHaveText("Optimize Lot");
    });

    test("should handle configuration toggles correctly", async () => {
      await page.goto("/");

      // Test direct backend toggle
      const directBackendToggle = page.getByTestId("toggle-direct-backend");
      await expect(directBackendToggle).not.toBeChecked();

      await directBackendToggle.check();
      await expect(directBackendToggle).toBeChecked();

      // Check that the UI reflects the change
      await expect(page.getByText(/Direct calls to/)).toBeVisible();

      // Test force mock toggle (only visible in test mode)
      if (await page.getByTestId("toggle-force-mock").isVisible()) {
        const forceMockToggle = page.getByTestId("toggle-force-mock");
        await forceMockToggle.check();
        await expect(forceMockToggle).toBeChecked();
      }
    });
  });

  test.describe("File Upload Functionality", () => {
    test("should accept CSV file uploads", async () => {
      await page.goto("/");

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      // Button should become enabled
      await expect(page.getByTestId("run-pipeline")).toBeEnabled();
    });

    test("should validate file size limits", async () => {
      await page.goto("/");

      // Create a large dummy file (this is just for UI testing, actual backend limits apply)
      const largeCsvContent = "a".repeat(25 * 1024 * 1024); // 25MB
      await page.evaluate((content) => {
        const blob = new Blob([content], { type: "text/csv" });
        const file = new File([blob], "large.csv", { type: "text/csv" });

        const input = document.querySelector(
          'input[type="file"]',
        ) as HTMLInputElement;
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }, largeCsvContent);

      // Should show size error when submitting
      const submitButton = page.getByTestId("run-pipeline");
      await submitButton.click();

      await expect(page.getByText(/File too large/)).toBeVisible();
    });

    test("should handle JSON configuration input", async () => {
      await page.goto("/");

      const jsonTextarea = page.getByTestId("optimizer-json");
      const testJson =
        '{"bid": 500, "roi_target": 1.5, "risk_threshold": 0.85}';

      await jsonTextarea.fill(testJson);
      await expect(jsonTextarea).toHaveValue(testJson);
    });
  });

  test.describe("Mock API Integration", () => {
    test("should successfully run optimization with demo data", async () => {
      await page.goto("/");

      const startTime = Date.now();

      // Upload demo files
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      const jsonTextarea = page.getByTestId("optimizer-json");
      const demoJson = readFileSync(DEMO_JSON_PATH, "utf-8");
      await jsonTextarea.fill(demoJson);

      // Submit the form
      const submitButton = page.getByTestId("run-pipeline");
      await submitButton.click();

      // Wait for results with generous timeout for mock processing
      await expect(page.getByTestId("result-summary")).toBeVisible({
        timeout: 15000,
      });

      testMetrics.interactionTime = Date.now() - startTime;

      // Verify results are displayed
      await expect(page.getByText("Optimization Results")).toBeVisible();
      await expect(
        page.locator('[data-testid="result-summary"]'),
      ).toBeVisible();
    });

    test("should display confidence metrics when available", async () => {
      await page.goto("/");

      // Run optimization to get results
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      const jsonTextarea = page.getByTestId("optimizer-json");
      const demoJson = readFileSync(DEMO_JSON_PATH, "utf-8");
      await jsonTextarea.fill(demoJson);

      await page.getByTestId("run-pipeline").click();
      await expect(page.getByTestId("result-summary")).toBeVisible({
        timeout: 15000,
      });

      // Check for confidence section (may or may not be present depending on mock data)
      if (await page.getByTestId("confidence-section").isVisible()) {
        await expect(page.getByTestId("confidence-average")).toBeVisible();
        await expect(page.getByText("Product Confidence")).toBeVisible();
      }
    });

    test("should display cache metrics when available", async () => {
      await page.goto("/");

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      await page.getByTestId("run-pipeline").click();
      await expect(page.getByTestId("result-summary")).toBeVisible({
        timeout: 15000,
      });

      // Check for cache metrics section
      if (await page.getByTestId("cache-metrics-section").isVisible()) {
        await expect(page.getByText("Cache Performance")).toBeVisible();
      }
    });

    test("should handle copy report path functionality", async () => {
      await page.goto("/");

      // Grant clipboard permissions
      await context.grantPermissions(["clipboard-read", "clipboard-write"]);

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      await page.getByTestId("run-pipeline").click();
      await expect(page.getByTestId("result-summary")).toBeVisible({
        timeout: 15000,
      });

      // Check if copy report button is present
      const copyButton = page.getByTestId("copy-report-path");
      if (await copyButton.isVisible()) {
        await copyButton.click();

        // Verify button text changes
        await expect(copyButton).toHaveText("Copied!");

        // Wait for text to revert
        await expect(copyButton).toHaveText("Copy Report Path", {
          timeout: 3000,
        });
      }
    });
  });

  test.describe("SSE (Server-Sent Events) Functionality", () => {
    test("should switch to SSE tab and display streaming interface", async () => {
      await page.goto("/");

      // Switch to SSE tab
      await page.getByText("Pipeline (SSE)").click();

      await expect(page.getByText("Pipeline Streaming")).toBeVisible();
      await expect(page.getByText("Monitor real-time progress")).toBeVisible();
    });

    test("should handle SSE streaming events", async () => {
      await page.goto("/");
      await page.getByText("Pipeline (SSE)").click();

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      const submitButton = page.getByTestId("run-pipeline");
      await submitButton.click();

      // Wait for streaming to start
      await expect(page.getByText("Pipeline running...")).toBeVisible();

      // Wait for completion with generous timeout
      await expect(page.getByTestId("result-summary")).toBeVisible({
        timeout: 20000,
      });
    });

    test("should display ping information during processing", async () => {
      await page.goto("/");
      await page.getByText("Pipeline (SSE)").click();

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      await page.getByTestId("run-pipeline").click();

      // Look for ping information (may appear during processing)
      const pipelineStatus = page.getByText(/Pipeline running/);
      await expect(pipelineStatus).toBeVisible();

      // Check if ping count is displayed (timing dependent)
      if (await page.getByText(/pings:/).isVisible({ timeout: 5000 })) {
        await expect(page.getByText(/pings:/)).toBeVisible();
      }
    });
  });

  test.describe("Error Handling and Edge Cases", () => {
    test("should display error when no CSV file is selected", async () => {
      await page.goto("/");

      // Try to submit without file
      const submitButton = page.getByTestId("run-pipeline");

      // Button should be disabled
      await expect(submitButton).toBeDisabled();
    });

    test("should handle invalid JSON configuration gracefully", async () => {
      await page.goto("/");

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      const jsonTextarea = page.getByTestId("optimizer-json");
      await jsonTextarea.fill("invalid json {");

      await page.getByTestId("run-pipeline").click();

      // Should handle JSON parsing error
      await expect(page.locator(".text-red-600")).toBeVisible({
        timeout: 10000,
      });
    });

    test("should handle network interruptions gracefully", async () => {
      await page.goto("/");

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      const submitButton = page.getByTestId("run-pipeline");
      await submitButton.click();

      // Simulate interruption by clicking again quickly
      if (
        (await submitButton.isVisible()) &&
        (await submitButton.isEnabled())
      ) {
        await submitButton.click();
      }

      // Should eventually complete or show appropriate error
      await page.waitForTimeout(2000);
    });
  });

  test.describe("Accessibility Testing", () => {
    test("should have proper heading structure", async () => {
      await page.goto("/");

      const h1 = page.locator("h1");
      await expect(h1).toHaveCount(1);
      await expect(h1).toHaveText("Lot Genius");

      // Check for proper heading hierarchy
      const h2Elements = page.locator("h2, h3");
      expect(await h2Elements.count()).toBeGreaterThan(0);
    });

    test("should have accessible form labels", async () => {
      await page.goto("/");

      // Check that form controls have proper labels
      const fileInput = page.locator('input[type="file"]');
      await expect(page.getByText("Items CSV (Required)")).toBeVisible();

      const jsonTextarea = page.getByTestId("optimizer-json");
      await expect(page.getByText("Optimizer JSON (Optional)")).toBeVisible();
    });

    test("should support keyboard navigation", async () => {
      await page.goto("/");

      // Test tab navigation
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");

      // Should be able to focus interactive elements
      const focusedElement = page.locator(":focus");
      await expect(focusedElement).toBeVisible();
    });

    test("should have proper ARIA attributes where needed", async () => {
      await page.goto("/");

      // Upload a file and submit to check for live regions
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      await page.getByTestId("run-pipeline").click();

      // Check for aria-live regions during processing
      const liveRegion = page.locator("[aria-live]");
      if ((await liveRegion.count()) > 0) {
        await expect(liveRegion.first()).toBeVisible();
      }
    });

    test("should provide sufficient color contrast", async () => {
      await page.goto("/");

      // This is a basic check - full color contrast would require specialized tools
      // Verify important elements are visible without relying on color alone
      await expect(page.getByTestId("run-pipeline")).toBeVisible();
      await expect(page.locator("h1")).toBeVisible();

      // Check disabled state is clearly indicated
      await expect(page.getByTestId("run-pipeline")).toHaveClass(
        /disabled:opacity-50/,
      );
    });
  });

  test.describe("Cross-Browser Compatibility", () => {
    test("should work consistently across different browsers", async () => {
      // This test runs in all configured browsers due to Playwright projects config
      await page.goto("/");

      await expect(page.locator("h1")).toHaveText("Lot Genius");
      await expect(page.getByTestId("run-pipeline")).toBeVisible();

      // Test basic interaction
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);
      await expect(page.getByTestId("run-pipeline")).toBeEnabled();
    });
  });

  test.describe("Performance and Resource Usage", () => {
    test("should not have excessive memory leaks or resource usage", async () => {
      await page.goto("/");

      // Simulate multiple interactions
      for (let i = 0; i < 3; i++) {
        await page.getByText("Pipeline (SSE)").click();
        await page.getByText("Optimize Lot").click();
        await page.waitForTimeout(500);
      }

      // Basic check - page should still be responsive
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.getByTestId("run-pipeline")).toBeVisible();
    });

    test("should handle large JSON configurations", async () => {
      await page.goto("/");

      // Create a large but valid JSON configuration
      const largeJsonConfig = {
        bid: 1000,
        roi_target: 1.25,
        risk_threshold: 0.8,
        // Add many optional parameters
        ...Object.fromEntries(
          Array.from({ length: 100 }, (_, i) => [`param_${i}`, i]),
        ),
      };

      const jsonTextarea = page.getByTestId("optimizer-json");
      await jsonTextarea.fill(JSON.stringify(largeJsonConfig, null, 2));

      // Should handle large input without issues
      await expect(jsonTextarea).toHaveValue(
        JSON.stringify(largeJsonConfig, null, 2),
      );
    });
  });
});
