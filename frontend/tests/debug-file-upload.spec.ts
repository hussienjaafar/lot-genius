import { test, expect } from "@playwright/test";
import { join } from "path";

// Test data path - fix the path issue
const DEMO_CSV_PATH = join(
  __dirname,
  "../../../examples/demo/demo_manifest.csv",
);

test.describe("Debug File Upload Issue", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("Debug: Check if demo CSV file exists", async ({ page }) => {
    // Log the path we're trying to use
    console.log("Looking for demo CSV at:", DEMO_CSV_PATH);

    // Check if file exists using Node.js fs
    const fs = require("fs");
    const fileExists = fs.existsSync(DEMO_CSV_PATH);
    console.log("Demo CSV file exists:", fileExists);

    if (!fileExists) {
      // Try alternative paths
      const altPath1 = join(__dirname, "../../examples/demo/demo_manifest.csv");
      const altPath2 = join(__dirname, "../examples/demo/demo_manifest.csv");

      console.log(
        "Trying alternative path 1:",
        altPath1,
        "exists:",
        fs.existsSync(altPath1),
      );
      console.log(
        "Trying alternative path 2:",
        altPath2,
        "exists:",
        fs.existsSync(altPath2),
      );

      // List what's actually in the examples directory
      try {
        const examplesPath = join(__dirname, "../../../examples");
        if (fs.existsSync(examplesPath)) {
          console.log(
            "Contents of examples directory:",
            fs.readdirSync(examplesPath),
          );
          const demoPath = join(examplesPath, "demo");
          if (fs.existsSync(demoPath)) {
            console.log(
              "Contents of demo directory:",
              fs.readdirSync(demoPath),
            );
          }
        }
      } catch (e) {
        console.log("Error listing directories:", e.message);
      }
    }
  });

  test("Debug: Examine file upload component behavior", async ({ page }) => {
    // Wait for page to load
    await expect(page.locator("h1")).toHaveText("Lot Genius");

    // Check if file input exists and is accessible
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
    console.log("File input found and attached");

    // Check the upload button state
    const submitButton = page.getByTestId("run-pipeline");
    const isDisabled = await submitButton.isDisabled();
    console.log("Submit button disabled:", isDisabled);

    // Check the drag-and-drop area
    const uploadArea = page.locator(".border-dashed");
    await expect(uploadArea).toBeVisible();
    console.log("Upload area is visible");

    // Try clicking the upload area
    await uploadArea.click();
    console.log("Clicked upload area");

    // Check if file dialog would open (we can't actually test this in headless)
    console.log(
      "File input accept attribute:",
      await fileInput.getAttribute("accept"),
    );

    // Create a test CSV content and try uploading
    const testCsvContent = "sku_local,title,condition\nTEST001,Test Item,New";

    // Create a test file using browser APIs
    await page.evaluate((content) => {
      const file = new File([content], "test.csv", { type: "text/csv" });
      const input = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      if (input) {
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;

        // Trigger change event
        input.dispatchEvent(new Event("change", { bubbles: true }));
        console.log("Test file created and assigned to input");
      }
    }, testCsvContent);

    // Wait a moment and check button state
    await page.waitForTimeout(1000);
    const isStillDisabled = await submitButton.isDisabled();
    console.log("Submit button disabled after file upload:", isStillDisabled);

    // Check if hasCsv state changed by looking at button attributes
    const buttonTitle = await submitButton.getAttribute("title");
    console.log("Button title attribute:", buttonTitle);
  });

  test("Debug: Test file upload with drag and drop simulation", async ({
    page,
  }) => {
    await expect(page.locator("h1")).toHaveText("Lot Genius");

    const uploadArea = page.locator(".border-dashed");
    const submitButton = page.getByTestId("run-pipeline");

    // Initial state
    console.log("Initial button disabled:", await submitButton.isDisabled());

    // Create a test file and simulate drag-drop
    await page.evaluate(() => {
      const file = new File(["sku_local,title\nTEST,Test Item"], "test.csv", {
        type: "text/csv",
      });

      // Find the upload area
      const uploadArea = document.querySelector(
        ".border-dashed",
      ) as HTMLElement;

      if (uploadArea) {
        // Create drag event
        const dragEvent = new DragEvent("drop", {
          bubbles: true,
          cancelable: true,
        });

        // Mock dataTransfer
        Object.defineProperty(dragEvent, "dataTransfer", {
          value: {
            files: [file],
            types: ["Files"],
            getData: () => "",
            setData: () => {},
            clearData: () => {},
            setDragImage: () => {},
          },
          writable: false,
        });

        // Trigger drop event
        uploadArea.dispatchEvent(dragEvent);
        console.log("Simulated drag-drop event");
      }
    });

    await page.waitForTimeout(1000);
    console.log(
      "Button disabled after drag-drop:",
      await submitButton.isDisabled(),
    );
  });

  test("Debug: Console errors and network requests", async ({ page }) => {
    // Listen for console messages
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        console.log("BROWSER ERROR:", msg.text());
      }
    });

    // Listen for failed network requests
    page.on("requestfailed", (request) => {
      console.log(
        "FAILED REQUEST:",
        request.url(),
        request.failure()?.errorText,
      );
    });

    await page.goto("/");
    await expect(page.locator("h1")).toHaveText("Lot Genius");

    // Wait for any async operations
    await page.waitForTimeout(2000);

    console.log("Page loaded, checking for errors...");
  });
});
