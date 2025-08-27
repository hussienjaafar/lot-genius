import { test, expect } from "@playwright/test";

test("Debug file type acceptance", async ({ page }) => {
  await page.goto("http://localhost:3002");

  // Check the file input accept attribute
  const fileInput = page.locator('input[type="file"]');
  const acceptAttr = await fileInput.getAttribute("accept");
  console.log("File input accept attribute:", acceptAttr);

  // Test different file types
  console.log("=== Testing different file types ===");

  // Test with different file extensions
  const testFiles = [
    { name: "test.csv", content: "sku,title\nTEST,Item", type: "text/csv" },
    { name: "test.CSV", content: "sku,title\nTEST,Item", type: "text/csv" },
    { name: "Excel.csv", content: "sku,title\nTEST,Item", type: "text/csv" },
    { name: "Excel.CSV", content: "sku,title\nTEST,Item", type: "text/csv" },
    {
      name: "data.csv",
      content: "sku,title\nTEST,Item",
      type: "application/csv",
    },
    {
      name: "spreadsheet.csv",
      content: "sku,title\nTEST,Item",
      type: "application/vnd.ms-excel",
    },
  ];

  for (const testFile of testFiles) {
    console.log(`\n--- Testing: ${testFile.name} (${testFile.type}) ---`);

    // Reset button state by refreshing
    await page.reload();
    await page.waitForLoadState("networkidle");

    const submitButton = page.getByTestId("run-pipeline");
    const initialDisabled = await submitButton.isDisabled();
    console.log("Initial button disabled:", initialDisabled);

    // Create and upload test file
    await page.evaluate(({ name, content, type }) => {
      const file = new File([content], name, { type: type });
      const input = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      if (input) {
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }, testFile);

    await page.waitForTimeout(500);

    const afterDisabled = await submitButton.isDisabled();
    console.log("After upload disabled:", afterDisabled);
    console.log(
      "Upload successful:",
      initialDisabled && !afterDisabled ? "✅" : "❌",
    );
  }

  console.log("\n=== Manual File Upload Test ===");
  console.log(
    "Try uploading your Excel.CSV file manually and check console for errors...",
  );

  // Listen for any file-related errors
  page.on("console", (msg) => {
    if (
      msg.type() === "error" ||
      msg.text().includes("file") ||
      msg.text().includes("CSV")
    ) {
      console.log("BROWSER:", msg.type().toUpperCase(), msg.text());
    }
  });

  // Wait for manual interaction
  await page.waitForTimeout(30000); // 30 seconds to manually test
});
