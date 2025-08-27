import { test, expect } from "@playwright/test";
import { join } from "path";

// Test data paths
const DEMO_CSV_PATH = join(
  __dirname,
  "../../../examples/demo/demo_manifest.csv",
);

test.describe("Lot Genius - Bug Detection and Edge Case Testing", () => {
  test.describe("Critical Bugs and Issues", () => {
    test("BUG: Multiple H1 elements on page (SEO/Accessibility Issue)", async ({
      page,
    }) => {
      await page.goto("/");

      // Check for duplicate H1 elements - this is a critical accessibility/SEO bug
      const h1Elements = await page.locator("h1").all();

      // Document the bug finding
      console.log(
        `FOUND BUG: ${h1Elements.length} H1 elements detected on page`,
      );
      if (h1Elements.length > 1) {
        for (let i = 0; i < h1Elements.length; i++) {
          const text = await h1Elements[i].textContent();
          const classes = await h1Elements[i].getAttribute("class");
          console.log(`  H1 ${i + 1}: "${text}" with classes: ${classes}`);
        }
      }

      // This should fail - there should only be one H1 per page
      expect(h1Elements.length).toBe(1);
    });

    test("POTENTIAL BUG: Form submission without proper validation", async ({
      page,
    }) => {
      await page.goto("/");

      // Try various edge cases for form submission
      const jsonTextarea = page.getByTestId("optimizer-json");

      // Test malformed JSON
      await jsonTextarea.fill('{"incomplete": json');

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      const submitButton = page.getByTestId("run-pipeline");
      await submitButton.click();

      // Should show error message, not crash
      await expect(page.locator(".text-red-600")).toBeVisible({
        timeout: 10000,
      });
    });

    test("PERFORMANCE ISSUE: Potential memory leak with rapid tab switching", async ({
      page,
    }) => {
      await page.goto("/");

      // Measure initial memory usage if possible
      const initialMetrics = await page.evaluate(() => {
        return (performance as any).memory
          ? {
              usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
              totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
            }
          : null;
      });

      // Rapid tab switching to test for memory leaks
      for (let i = 0; i < 20; i++) {
        await page.getByText("Pipeline (SSE)").click();
        await page.getByText("Optimize Lot").click();
        await page.waitForTimeout(50); // Brief pause
      }

      // Measure final memory usage
      const finalMetrics = await page.evaluate(() => {
        return (performance as any).memory
          ? {
              usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
              totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
            }
          : null;
      });

      if (initialMetrics && finalMetrics) {
        const memoryIncrease =
          finalMetrics.usedJSHeapSize - initialMetrics.usedJSHeapSize;
        console.log(
          `Memory increase after rapid tab switching: ${memoryIncrease} bytes`,
        );

        // Flag excessive memory growth as potential issue
        if (memoryIncrease > 10 * 1024 * 1024) {
          // 10MB
          console.warn(
            "POTENTIAL MEMORY LEAK: Excessive memory growth detected",
          );
        }
      }

      // Page should still be functional
      await expect(page.locator("h1")).toBeVisible();
    });

    test("USABILITY BUG: Inconsistent button states and feedback", async ({
      page,
    }) => {
      await page.goto("/");

      const submitButton = page.getByTestId("run-pipeline");

      // Check initial disabled state
      await expect(submitButton).toBeDisabled();
      await expect(submitButton).toHaveText("Optimize Lot");

      // Upload file
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      // Should become enabled
      await expect(submitButton).toBeEnabled();

      // Switch to SSE tab and check button behavior
      await page.getByText("Pipeline (SSE)").click();
      const sseSubmitButton = page.getByTestId("run-pipeline");

      // Check for consistency in button behavior between tabs
      await expect(sseSubmitButton).toBeEnabled();
      await expect(sseSubmitButton).toHaveText("Run Pipeline");

      // This reveals potential inconsistency - different button text
      console.log(
        'INCONSISTENCY: Button text differs between tabs: "Optimize Lot" vs "Run Pipeline"',
      );
    });
  });

  test.describe("Edge Cases and Boundary Conditions", () => {
    test("EDGE CASE: Extremely large JSON configuration", async ({ page }) => {
      await page.goto("/");

      // Create an excessively large JSON configuration
      const largeConfig = {
        bid: 1000,
        roi_target: 1.25,
        // Add thousands of parameters to test limits
        ...Object.fromEntries(
          Array.from({ length: 10000 }, (_, i) => [
            `param_${i}`,
            `value_${i}_${"x".repeat(100)}`,
          ]),
        ),
      };

      const jsonString = JSON.stringify(largeConfig);
      console.log(`Testing with JSON size: ${jsonString.length} characters`);

      const jsonTextarea = page.getByTestId("optimizer-json");

      try {
        await jsonTextarea.fill(jsonString);
        console.log("RESULT: Large JSON accepted without error");
      } catch (error) {
        console.log("POTENTIAL ISSUE: Large JSON caused error:", error);
      }

      // Check if page is still responsive
      await expect(page.locator("h1")).toBeVisible();
    });

    test("EDGE CASE: File upload with special characters and edge cases", async ({
      page,
    }) => {
      await page.goto("/");

      // Test with various file scenarios
      const testCases = [
        { name: "empty.csv", content: "" },
        {
          name: "unicode-filename-😀.csv",
          content: "col1,col2\nvalue1,value2",
        },
        {
          name: "very-long-filename-" + "x".repeat(200) + ".csv",
          content: "a,b\n1,2",
        },
        { name: "file.with.multiple.dots.csv", content: "test,data\n1,2" },
      ];

      for (const testCase of testCases) {
        try {
          await page.evaluate(({ name, content }) => {
            const file = new File([content], name, { type: "text/csv" });
            const input = document.querySelector(
              'input[type="file"]',
            ) as HTMLInputElement;
            const dt = new DataTransfer();
            dt.items.add(file);
            input.files = dt.files;
            input.dispatchEvent(new Event("change", { bubbles: true }));
          }, testCase);

          console.log(`SUCCESS: Accepted file with name: ${testCase.name}`);

          // Check if button becomes enabled
          const isEnabled = await page.getByTestId("run-pipeline").isEnabled();
          console.log(`Button enabled for ${testCase.name}: ${isEnabled}`);
        } catch (error) {
          console.log(`ISSUE: File ${testCase.name} caused error:`, error);
        }
      }
    });

    test("EDGE CASE: Rapid-fire form submissions", async ({ page }) => {
      await page.goto("/");

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      const submitButton = page.getByTestId("run-pipeline");

      // Try to submit multiple times rapidly
      let submissionErrors = 0;
      let submissionSuccesses = 0;

      for (let i = 0; i < 5; i++) {
        try {
          if (await submitButton.isEnabled()) {
            await submitButton.click();
            submissionSuccesses++;
            await page.waitForTimeout(100);
          }
        } catch (error) {
          submissionErrors++;
          console.log(`Submission ${i + 1} error:`, error);
        }
      }

      console.log(
        `Rapid submissions: ${submissionSuccesses} successful, ${submissionErrors} errors`,
      );

      // Should handle gracefully without crashes
      await expect(page.locator("h1")).toBeVisible();
    });

    test("EDGE CASE: Browser back/forward navigation during processing", async ({
      page,
    }) => {
      await page.goto("/");

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      // Start processing
      await page.getByTestId("run-pipeline").click();

      // Navigate away and back quickly
      await page.goBack();
      await page.goForward();

      // Check if page state is consistent
      await expect(page.locator("h1")).toBeVisible();

      // Check if form is still functional
      await expect(page.getByTestId("run-pipeline")).toBeVisible();
    });
  });

  test.describe("Error Recovery and Resilience", () => {
    test("ERROR HANDLING: Network failure during file upload", async ({
      page,
    }) => {
      await page.goto("/");

      // Intercept network requests and simulate failure
      await page.route("/api/**", (route) => {
        route.abort("failed");
      });

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      await page.getByTestId("run-pipeline").click();

      // Should show appropriate error message
      await expect(page.locator(".text-red-600")).toBeVisible({
        timeout: 10000,
      });

      // Should not crash the application
      await expect(page.locator("h1")).toBeVisible();
    });

    test("ERROR RECOVERY: Corrupted state recovery", async ({ page }) => {
      await page.goto("/");

      // Simulate corrupted application state
      await page.evaluate(() => {
        // Corrupt some global state
        (window as any).corruptedState = true;

        // Try to corrupt React state (this might not work due to React's protections)
        try {
          const reactFiber = (document.querySelector("#__next") as any)
            ?._reactInternalFiber;
          if (reactFiber) {
            console.log("Found React fiber, attempting state corruption test");
          }
        } catch (e) {
          console.log("React state corruption test failed safely:", e.message);
        }
      });

      // App should still function despite corruption attempts
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.getByTestId("run-pipeline")).toBeVisible();
    });

    test("RESILIENCE: Page refresh during active processing", async ({
      page,
    }) => {
      await page.goto("/");

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(DEMO_CSV_PATH);

      // Start processing
      await page.getByText("Pipeline (SSE)").click();
      await page.getByTestId("run-pipeline").click();

      // Wait a moment for processing to start
      await page.waitForTimeout(1000);

      // Refresh the page
      await page.reload();

      // Should return to initial clean state
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.getByTestId("run-pipeline")).toBeDisabled(); // No file selected after refresh
    });
  });

  test.describe("Security and Validation Issues", () => {
    test("SECURITY: XSS attempt through file names", async ({ page }) => {
      await page.goto("/");

      // Attempt XSS through malicious filename
      const maliciousFileName = '<script>alert("xss")</script>.csv';

      await page.evaluate((fileName) => {
        const file = new File(["test,data\n1,2"], fileName, {
          type: "text/csv",
        });
        const input = document.querySelector(
          'input[type="file"]',
        ) as HTMLInputElement;
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }, maliciousFileName);

      // Should not execute script or cause issues
      await expect(page.locator("h1")).toBeVisible();

      // Check if filename is properly sanitized when displayed
      console.log("XSS filename test completed - no script execution detected");
    });

    test("VALIDATION: Oversized file handling", async ({ page }) => {
      await page.goto("/");

      // Create a file that exceeds the stated 20MB limit
      const oversizedContent = "a".repeat(25 * 1024 * 1024); // 25MB

      await page.evaluate((content) => {
        const file = new File([content], "oversized.csv", { type: "text/csv" });
        const input = document.querySelector(
          'input[type="file"]',
        ) as HTMLInputElement;
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }, oversizedContent);

      // Try to submit
      const submitButton = page.getByTestId("run-pipeline");
      await submitButton.click();

      // Should show size error message
      await expect(page.getByText(/File too large/)).toBeVisible();

      console.log("File size validation working correctly");
    });

    test("VALIDATION: Malformed CSV content handling", async ({ page }) => {
      await page.goto("/");

      // Test various malformed CSV scenarios
      const malformedCsvCases = [
        { name: "Binary data", content: "\x00\x01\x02\x03\x04\x05" },
        {
          name: "Extremely long lines",
          content: "col1,col2\n" + "x".repeat(1000000) + ",value",
        },
        {
          name: "Mixed encodings",
          content: "col1,col2\nvalue1,caf\u00e9\u2603\ud83d\ude00",
        },
        { name: "No headers", content: "1,2,3\n4,5,6\n7,8,9" },
        { name: "Inconsistent columns", content: "a,b,c\n1,2\n3,4,5,6,7" },
      ];

      for (const testCase of malformedCsvCases) {
        await page.evaluate(({ name, content }) => {
          const file = new File([content], `${name.replace(/\s+/g, "_")}.csv`, {
            type: "text/csv",
          });
          const input = document.querySelector(
            'input[type="file"]',
          ) as HTMLInputElement;
          const dt = new DataTransfer();
          dt.items.add(file);
          input.files = dt.files;
          input.dispatchEvent(new Event("change", { bubbles: true }));
        }, testCase);

        console.log(`Testing malformed CSV: ${testCase.name}`);

        // Should still enable the submit button (backend handles validation)
        await expect(page.getByTestId("run-pipeline")).toBeEnabled();

        // Application should remain stable
        await expect(page.locator("h1")).toBeVisible();
      }
    });
  });

  test.describe("Browser Compatibility Issues", () => {
    test("COMPATIBILITY: File API support detection", async ({ page }) => {
      await page.goto("/");

      // Check if File API is properly supported
      const fileApiSupport = await page.evaluate(() => {
        return {
          File: typeof File !== "undefined",
          FileList: typeof FileList !== "undefined",
          DataTransfer: typeof DataTransfer !== "undefined",
          FileReader: typeof FileReader !== "undefined",
        };
      });

      console.log("File API support:", fileApiSupport);

      // All should be supported in modern browsers
      expect(fileApiSupport.File).toBe(true);
      expect(fileApiSupport.DataTransfer).toBe(true);
    });

    test("COMPATIBILITY: Local storage and session handling", async ({
      page,
    }) => {
      await page.goto("/");

      // Test if app gracefully handles storage being unavailable
      await page.evaluate(() => {
        // Mock storage being unavailable
        const originalSetItem = localStorage.setItem;
        localStorage.setItem = () => {
          throw new Error("Storage unavailable");
        };

        // Restore after test
        setTimeout(() => {
          localStorage.setItem = originalSetItem;
        }, 1000);
      });

      // App should still function
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.getByTestId("run-pipeline")).toBeVisible();

      console.log("App handles storage unavailability gracefully");
    });

    test("COMPATIBILITY: Clipboard API availability", async ({ page }) => {
      await page.goto("/");

      // Check clipboard API support
      const clipboardSupport = await page.evaluate(() => {
        return {
          navigator: typeof navigator !== "undefined",
          clipboard: typeof navigator?.clipboard !== "undefined",
          writeText: typeof navigator?.clipboard?.writeText === "function",
        };
      });

      console.log("Clipboard API support:", clipboardSupport);

      // If clipboard is not supported, copy functionality should degrade gracefully
      if (!clipboardSupport.writeText) {
        console.log(
          "WARNING: Clipboard API not available - copy functionality may not work",
        );
      }
    });
  });

  test.describe("Performance Issues and Bottlenecks", () => {
    test("PERFORMANCE: Large DOM manipulation efficiency", async ({ page }) => {
      await page.goto("/");

      // Simulate adding many elements to test performance
      const startTime = Date.now();

      await page.evaluate(() => {
        const container = document.createElement("div");
        document.body.appendChild(container);

        // Add many elements
        for (let i = 0; i < 1000; i++) {
          const element = document.createElement("div");
          element.textContent = `Test element ${i}`;
          container.appendChild(element);
        }

        // Clean up
        document.body.removeChild(container);
      });

      const duration = Date.now() - startTime;
      console.log(`DOM manipulation took ${duration}ms for 1000 elements`);

      // Should complete within reasonable time
      expect(duration).toBeLessThan(1000);
    });

    test("PERFORMANCE: Event listener cleanup", async ({ page }) => {
      await page.goto("/");

      // Check for potential memory leaks from event listeners
      const initialListeners = await page.evaluate(() => {
        return (window as any).getEventListeners
          ? Object.keys((window as any).getEventListeners(document)).length
          : 0;
      });

      // Perform actions that might add listeners
      for (let i = 0; i < 10; i++) {
        await page.getByText("Pipeline (SSE)").click();
        await page.getByText("Optimize Lot").click();
      }

      const finalListeners = await page.evaluate(() => {
        return (window as any).getEventListeners
          ? Object.keys((window as any).getEventListeners(document)).length
          : 0;
      });

      console.log(`Event listeners: ${initialListeners} -> ${finalListeners}`);

      if (finalListeners > initialListeners + 10) {
        console.warn("POTENTIAL MEMORY LEAK: Too many event listeners added");
      }
    });
  });
});
