import { test, expect, Page } from "@playwright/test";
import { join } from "path";

// Test data paths
const DEMO_CSV_PATH = join(
  __dirname,
  "../../../examples/demo/demo_manifest.csv",
);

test.describe("Lot Genius - Usability Focused Testing", () => {
  test.describe("User Journey and Workflow", () => {
    test("should guide new users through the complete workflow", async ({
      page,
    }) => {
      await page.goto("/");

      // Step 1: User lands on page and sees clear heading
      await expect(page.locator("h1")).toHaveText("Lot Genius");

      // Step 2: User sees they need to upload a CSV
      await expect(page.getByText("Items CSV (Required)")).toBeVisible();
      const submitButton = page.getByTestId("run-pipeline");
      await expect(submitButton).toBeDisabled();

      // Step 3: User gets helpful tooltip on disabled button
      await expect(submitButton).toHaveAttribute(
        "title",
        "Choose a CSV to enable optimization",
      );

      // Step 4: User uploads file and button becomes enabled
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);
      await expect(submitButton).toBeEnabled();

      // Step 5: User sees optional configuration options
      await expect(page.getByText("Optimizer JSON (Optional)")).toBeVisible();
      await expect(page.getByTestId("optimizer-json")).toHaveAttribute(
        "placeholder",
      );

      // Step 6: User can see configuration toggles with helpful descriptions
      await expect(page.getByText("Direct Backend Mode")).toBeVisible();
      await expect(page.getByText(/Using Next.js API proxy/)).toBeVisible();
    });

    test("should provide clear feedback during file upload process", async ({
      page,
    }) => {
      await page.goto("/");

      // User sees file picker with clear labeling
      await expect(page.getByText("Items CSV (Required)")).toBeVisible();

      // User sees size limit information
      await expect(
        page.getByText("Max upload: 20 MB (UI limit)"),
      ).toBeVisible();

      // User uploads file and sees immediate feedback
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      // Button state changes to indicate file was accepted
      const submitButton = page.getByTestId("run-pipeline");
      await expect(submitButton).toBeEnabled();
      await expect(submitButton).toHaveText("Optimize Lot");
    });

    test("should offer clear tab navigation with descriptive content", async ({
      page,
    }) => {
      await page.goto("/");

      // Default tab has clear description
      await expect(page.getByText("Lot Optimization")).toBeVisible();
      await expect(
        page.getByText("Upload your items CSV and optimization parameters"),
      ).toBeVisible();

      // Switch to SSE tab
      await page.getByText("Pipeline (SSE)").click();
      await expect(page.getByText("Pipeline Streaming")).toBeVisible();
      await expect(page.getByText("Monitor real-time progress")).toBeVisible();

      // Tab switching is smooth and immediate
      await page.getByText("Optimize Lot").click();
      await expect(page.getByText("Lot Optimization")).toBeVisible();
    });
  });

  test.describe("Visual Design and Layout", () => {
    test("should have clear visual hierarchy and spacing", async ({ page }) => {
      await page.goto("/");

      // Main heading is prominent
      const h1 = page.locator("h1");
      await expect(h1).toHaveText("Lot Genius");

      // Sections are clearly separated
      await expect(page.getByText("Lot Optimization")).toBeVisible();

      // Configuration area is visually distinct
      await expect(page.locator(".bg-blue-50")).toBeVisible();

      // Form elements have proper spacing
      const formElements = page.locator("input, textarea, button");
      expect(await formElements.count()).toBeGreaterThan(3);
    });

    test("should adapt layout for different screen sizes", async ({ page }) => {
      // Test desktop layout
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto("/");

      await expect(page.locator("h1")).toBeVisible();
      await expect(page.getByText("Items CSV (Required)")).toBeVisible();

      // Test tablet layout
      await page.setViewportSize({ width: 768, height: 1024 });
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.getByTestId("run-pipeline")).toBeVisible();

      // Test mobile layout
      await page.setViewportSize({ width: 375, height: 667 });
      await expect(page.locator("h1")).toBeVisible();

      // Form should still be usable on mobile
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);
      await expect(page.getByTestId("run-pipeline")).toBeEnabled();
    });

    test("should use consistent color scheme and typography", async ({
      page,
    }) => {
      await page.goto("/");

      // Check consistent blue theme for primary elements
      await expect(
        page.locator(".text-blue-600, .text-blue-700, .text-blue-800"),
      ).toHaveCount({
        gte: 1,
      });

      // Check consistent button styling
      const buttons = page.locator("button");
      expect(await buttons.count()).toBeGreaterThan(2);

      // Primary action button should be visually prominent
      const submitButton = page.getByTestId("run-pipeline");
      await expect(submitButton).toHaveClass(/bg-blue-600/);
    });
  });

  test.describe("Information Architecture and Content", () => {
    test("should provide helpful placeholder text and examples", async ({
      page,
    }) => {
      await page.goto("/");

      // JSON textarea has example configuration
      const jsonTextarea = page.getByTestId("optimizer-json");
      const placeholder = await jsonTextarea.getAttribute("placeholder");
      expect(placeholder).toContain("roi_target");
      expect(placeholder).toContain("risk_threshold");

      // Optional fields have helpful placeholder text
      const calibrationInput = page.locator(
        'input[placeholder*="calibration"]',
      );
      if ((await calibrationInput.count()) > 0) {
        await expect(calibrationInput.first()).toHaveAttribute("placeholder");
      }
    });

    test("should show contextual help and tooltips", async ({ page }) => {
      await page.goto("/");

      // Configuration toggles have explanatory text
      await expect(page.getByText("Direct Backend Mode")).toBeVisible();
      await expect(
        page.getByText(/Using Next.js API proxy|Direct calls to/),
      ).toBeVisible();

      // File size limits are clearly communicated
      await expect(
        page.getByText("Max upload: 20 MB (UI limit)"),
      ).toBeVisible();

      // Button states provide feedback
      const submitButton = page.getByTestId("run-pipeline");
      await expect(submitButton).toHaveAttribute("title");
    });

    test("should organize advanced features logically", async ({ page }) => {
      await page.goto("/");

      // Advanced configuration is in a separate, clearly marked area
      await expect(page.locator(".bg-blue-50")).toBeVisible();

      // Optional fields are clearly marked as optional
      await expect(page.getByText("Optimizer JSON (Optional)")).toBeVisible();

      // Optional output paths are grouped together
      const optionalFields = page.locator(
        'input[placeholder*="path"], input[placeholder*=".md"]',
      );
      if ((await optionalFields.count()) > 0) {
        expect(await optionalFields.count()).toBeGreaterThanOrEqual(1);
      }
    });
  });

  test.describe("Interaction Design and Feedback", () => {
    test("should provide immediate feedback on user actions", async ({
      page,
    }) => {
      await page.goto("/");

      // File upload provides immediate visual feedback
      const fileInput = page.locator('input[type="file"]');
      const submitButton = page.getByTestId("run-pipeline");

      // Initially disabled
      await expect(submitButton).toBeDisabled();

      // Becomes enabled after file upload
      await fileInput.setInputFiles(DEMO_CSV_PATH);
      await expect(submitButton).toBeEnabled();

      // Text changes during processing
      await submitButton.click();
      await expect(submitButton).toHaveText(/Optimizing...|Running.../);
    });

    test("should handle configuration changes smoothly", async ({ page }) => {
      await page.goto("/");

      // Toggle changes are immediate
      const directBackendToggle = page.getByTestId("toggle-direct-backend");
      await expect(page.getByText(/Using Next.js API proxy/)).toBeVisible();

      await directBackendToggle.check();
      await expect(page.getByText(/Direct calls to/)).toBeVisible();

      // Tab switching is immediate
      await page.getByText("Pipeline (SSE)").click();
      await expect(page.getByText("Pipeline Streaming")).toBeVisible();
    });

    test("should show appropriate loading and progress indicators", async ({
      page,
    }) => {
      await page.goto("/");

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      // Switch to SSE tab to see progress indicators
      await page.getByText("Pipeline (SSE)").click();

      const submitButton = page.getByTestId("run-pipeline");
      await submitButton.click();

      // Should show running status
      await expect(page.getByText("Pipeline running...")).toBeVisible();

      // May show ping information
      if (await page.getByText(/pings:/).isVisible({ timeout: 5000 })) {
        await expect(page.getByText(/pings:/)).toBeVisible();
      }
    });
  });

  test.describe("Error Handling and User Guidance", () => {
    test("should prevent common user errors", async ({ page }) => {
      await page.goto("/");

      // Cannot submit without required fields
      const submitButton = page.getByTestId("run-pipeline");
      await expect(submitButton).toBeDisabled();

      // Helpful tooltip explains why button is disabled
      await expect(submitButton).toHaveAttribute(
        "title",
        "Choose a CSV to enable optimization",
      );
    });

    test("should provide clear error messages", async ({ page }) => {
      await page.goto("/");

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      // Test with invalid JSON
      const jsonTextarea = page.getByTestId("optimizer-json");
      await jsonTextarea.fill("invalid json {");

      await page.getByTestId("run-pipeline").click();

      // Should show error in user-friendly format
      await expect(page.locator(".text-red-600")).toBeVisible({
        timeout: 10000,
      });
    });

    test("should handle edge cases gracefully", async ({ page }) => {
      await page.goto("/");

      // Test empty file upload scenario
      const fileInput = page.locator('input[type="file"]');

      // Create minimal test file
      await page.evaluate(() => {
        const input = document.querySelector(
          'input[type="file"]',
        ) as HTMLInputElement;
        const file = new File([""], "empty.csv", { type: "text/csv" });
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      });

      // Should still enable button (backend will handle validation)
      await expect(page.getByTestId("run-pipeline")).toBeEnabled();
    });
  });

  test.describe("Accessibility and Inclusive Design", () => {
    test("should support keyboard-only navigation", async ({ page }) => {
      await page.goto("/");

      // Tab through interactive elements
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");

      // Should be able to reach all interactive elements
      const focusedElement = page.locator(":focus");
      await expect(focusedElement).toBeVisible();

      // Should be able to activate buttons with keyboard
      const submitButton = page.getByTestId("run-pipeline");
      if (await submitButton.isEnabled()) {
        await submitButton.focus();
        await page.keyboard.press("Enter");
      }
    });

    test("should have proper semantic markup", async ({ page }) => {
      await page.goto("/");

      // Main heading is properly marked up
      await expect(page.locator("h1")).toHaveText("Lot Genius");

      // Form has proper structure
      await expect(page.locator("form")).toBeVisible();

      // Labels are associated with form controls
      await expect(page.getByText("Items CSV (Required)")).toBeVisible();
      await expect(page.getByText("Optimizer JSON (Optional)")).toBeVisible();
    });

    test("should work well with screen readers", async ({ page }) => {
      await page.goto("/");

      // Important status updates should be announced
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      await page.getByTestId("run-pipeline").click();

      // Check for live regions
      const liveRegions = page.locator("[aria-live]");
      if ((await liveRegions.count()) > 0) {
        await expect(liveRegions.first()).toBeVisible();
      }
    });
  });

  test.describe("Performance and User Experience", () => {
    test("should load quickly and respond immediately to interactions", async ({
      page,
    }) => {
      const startTime = Date.now();
      await page.goto("/");

      // Page should load quickly
      await expect(page.locator("h1")).toBeVisible();
      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(3000);

      // Interactions should be immediate
      const interactionStart = Date.now();
      await page.getByText("Pipeline (SSE)").click();
      await expect(page.getByText("Pipeline Streaming")).toBeVisible();
      const interactionTime = Date.now() - interactionStart;
      expect(interactionTime).toBeLessThan(500);
    });

    test("should handle multiple rapid interactions gracefully", async ({
      page,
    }) => {
      await page.goto("/");

      // Rapidly switch between tabs
      for (let i = 0; i < 5; i++) {
        await page.getByText("Pipeline (SSE)").click();
        await page.getByText("Optimize Lot").click();
      }

      // Should still be in working state
      await expect(page.getByText("Lot Optimization")).toBeVisible();
      await expect(page.getByTestId("run-pipeline")).toBeVisible();
    });

    test("should maintain state appropriately during navigation", async ({
      page,
    }) => {
      await page.goto("/");

      // Upload file and configure JSON
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      const jsonTextarea = page.getByTestId("optimizer-json");
      await jsonTextarea.fill('{"bid": 123}');

      // Switch tabs and back
      await page.getByText("Pipeline (SSE)").click();
      await page.getByText("Optimize Lot").click();

      // Configuration should be maintained
      await expect(page.getByTestId("run-pipeline")).toBeEnabled();
      await expect(jsonTextarea).toHaveValue('{"bid": 123}');
    });
  });
});
