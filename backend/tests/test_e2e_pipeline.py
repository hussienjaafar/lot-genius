"""End-to-end test for the Lot Genius pipeline using Playwright."""

import asyncio
import os
import time
from pathlib import Path

import pytest
import requests


def check_frontend_running(frontend_url: str) -> bool:
    """Check if the frontend is running by making a GET request."""
    try:
        response = requests.get(frontend_url, timeout=5)
        return response.status_code == 200
    except (requests.RequestException, ConnectionError):
        return False


@pytest.mark.asyncio
async def test_complete_pipeline_e2e():
    """Test the complete pipeline from file upload to results display."""

    # Import playwright here to avoid import issues if not installed
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        pytest.skip("Playwright not installed")

    # Read frontend URL from environment
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3002")

    # Preflight check - skip if frontend not running
    if not check_frontend_running(frontend_url):
        pytest.skip(f"Frontend not running at {frontend_url}")

    test_manifest_path = Path("C:/Users/Husse/lot-genius/test_manifest.csv")

    # Ensure test file exists
    assert (
        test_manifest_path.exists()
    ), f"Test manifest file not found at {test_manifest_path}"

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Listen for console messages and network requests
            page.on("console", lambda msg: print(f"Console: {msg.text}"))
            page.on("request", lambda req: print(f"Request: {req.method} {req.url}"))
            page.on(
                "response", lambda resp: print(f"Response: {resp.status} {resp.url}")
            )

            # Navigate to the frontend
            await page.goto(frontend_url)

            # Wait for page to load using robust selector
            await page.wait_for_selector("h1:has-text('Lot Genius')", timeout=10000)

            # Switch to SSE tab for testing
            sse_tab_button = page.get_by_text("Pipeline (SSE)")
            await sse_tab_button.click()

            # If force-mock toggle exists, click it before submitting
            force_mock_toggle = page.get_by_test_id("toggle-force-mock")
            if await force_mock_toggle.count() > 0:
                await force_mock_toggle.click()
                print("Enabled force-mock toggle for testing")
                # Verify it's checked
                is_checked = await force_mock_toggle.is_checked()
                assert is_checked, "Force-mock toggle should be checked after clicking"
            else:
                print(
                    "Force-mock toggle not found - test environment may not have NEXT_PUBLIC_TEST=1"
                )

            # Upload file using data-testid
            file_input = page.get_by_test_id("file-input")
            await file_input.set_input_files(str(test_manifest_path))

            # Wait for file to be processed and button to be enabled
            run_button = page.get_by_test_id("run-pipeline")
            await page.wait_for_function(
                "() => !document.querySelector('[data-testid=\"run-pipeline\"]').disabled",
                timeout=5000,
            )

            # Set up request monitoring with more detailed logging
            mock_request_detected = False
            all_requests = []

            def handle_request(request):
                nonlocal mock_request_detected
                all_requests.append(f"{request.method} {request.url}")
                if "/api/mock/pipeline/upload/stream" in request.url:
                    mock_request_detected = True
                    print(
                        f"SUCCESS: Mock API request detected: {request.method} {request.url}"
                    )
                    return
                # Also log other API requests for debugging
                if "/api/" in request.url and "/node_modules" not in request.url:
                    print(f"API Request: {request.method} {request.url}")

            page.on("request", handle_request)

            # Click the run button
            await run_button.click()

            # Wait for either the mock API request or the first SSE event
            try:
                # Try to wait for the mock API request
                await page.wait_for_request(
                    lambda req: "/api/mock/pipeline/upload/stream" in req.url,
                    timeout=10000,
                )
                mock_request_detected = True
                print("SUCCESS: Mock API request detected via wait_for_request")
            except:
                print(
                    "WARNING: wait_for_request timeout - checking if request was detected by handler"
                )
                if not mock_request_detected:
                    print(
                        f"All requests captured: {all_requests[-10:]}"
                    )  # Show last 10 requests

            # Wait for SSE console to appear and show events
            sse_console = page.get_by_test_id("sse-console")
            await sse_console.wait_for(state="visible", timeout=5000)

            # Wait for the submit event to appear (visible instrumentation)
            submit_detected = False
            for i in range(15):  # Wait up to 15 seconds for submit event
                console_text = await sse_console.text_content()
                if (
                    "submit:" in console_text.lower()
                    or "submitting sse request" in console_text.lower()
                ):
                    print("SUCCESS: Submit event detected in SSE console")
                    submit_detected = True
                    break
                elif (
                    console_text.strip() and "no events yet" not in console_text.lower()
                ):
                    print(f"Console activity detected: {console_text[:100]}...")
                await asyncio.sleep(1)

            assert (
                submit_detected
            ), f"Submit event not detected in SSE console. Final console: {await sse_console.text_content()}"

            # Monitor for specific phase progression
            phases_to_check = [
                "start",
                "parse",
                "validate",
                "enrich_keepa",
                "price",
                "sell",
                "evidence",
                "optimize",
                "render_report",
                "done",
            ]
            detected_phases = set()

            # Wait up to 30 seconds for pipeline completion
            max_wait_time = 30000
            start_time = time.time()

            while (time.time() - start_time) * 1000 < max_wait_time:
                console_text = await sse_console.text_content()

                # Check for phases in the console output
                for phase in phases_to_check:
                    if phase in console_text and phase not in detected_phases:
                        detected_phases.add(phase)
                        print(f"Detected phase: {phase}")

                # Check for completion
                if "done" in detected_phases or "pipeline_complete" in console_text:
                    print("Pipeline completion detected!")
                    break

                # Check for errors
                if "error" in console_text.lower():
                    print(f"Error detected in console: {console_text}")
                    break

                await asyncio.sleep(1)

            # Final console state
            final_console = await sse_console.text_content()
            print(f"Final console state: {final_console[:500]}...")

            # Verify critical phase order: evidence should come between sell and optimize
            console_lines = final_console.lower().split("\n")
            sell_line_idx = None
            evidence_line_idx = None
            optimize_line_idx = None

            for i, line in enumerate(console_lines):
                if "sell:" in line and sell_line_idx is None:
                    sell_line_idx = i
                elif "evidence:" in line and evidence_line_idx is None:
                    evidence_line_idx = i
                elif "optimize:" in line and optimize_line_idx is None:
                    optimize_line_idx = i

            # Check phase order (evidence between sell and optimize)
            if (
                sell_line_idx is not None
                and evidence_line_idx is not None
                and optimize_line_idx is not None
            ):
                assert (
                    sell_line_idx < evidence_line_idx < optimize_line_idx
                ), f"Phase order incorrect: sell({sell_line_idx}) -> evidence({evidence_line_idx}) -> optimize({optimize_line_idx})"
                print(
                    "SUCCESS: Phase order assertion passed: evidence comes between sell and optimize"
                )

            # Check results summary if available
            try:
                results_section = page.get_by_test_id("result-summary")
                results_visible = await results_section.is_visible()
                if results_visible:
                    results_text = await results_section.text_content()
                    print(f"Results summary visible: {results_text[:200]}...")

                    # Check for Product Confidence section when mock adds confidence_samples
                    confidence_section = page.get_by_test_id("confidence-section")
                    if await confidence_section.count() > 0:
                        confidence_text = await confidence_section.text_content()
                        print(
                            f"SUCCESS: Product Confidence section detected: {confidence_text[:100]}..."
                        )

                        # Verify confidence average is displayed
                        confidence_avg = page.get_by_test_id("confidence-average")
                        if await confidence_avg.count() > 0:
                            avg_text = await confidence_avg.text_content()
                            print(f"SUCCESS: Confidence average displayed: {avg_text}")
                            # Verify it's a valid number between 0-1
                            try:
                                avg_val = float(avg_text)
                                assert (
                                    0 <= avg_val <= 1
                                ), f"Confidence average {avg_val} not in range [0,1]"
                                print(
                                    f"SUCCESS: Confidence average {avg_val} is in valid range"
                                )
                            except ValueError:
                                print(
                                    f"WARNING: Confidence average '{avg_text}' is not a valid number"
                                )
                    else:
                        print(
                            "INFO: Product Confidence section not displayed (no confidence_samples in mock)"
                        )

                    # Check for Cache Metrics section when cache_stats present in mock
                    cache_section = page.get_by_test_id("cache-metrics-section")
                    if await cache_section.count() > 0:
                        cache_text = await cache_section.text_content()
                        print(
                            f"SUCCESS: Cache Metrics section detected: {cache_text[:100]}..."
                        )

                        # Check specific cache entries
                        keepa_cache = page.get_by_test_id("cache-keepa_cache")
                        ebay_cache = page.get_by_test_id("cache-ebay_cache")

                        if await keepa_cache.count() > 0:
                            keepa_text = await keepa_cache.text_content()
                            print(f"SUCCESS: Keepa cache metrics: {keepa_text}")
                            # Verify hits/misses/hit ratio format
                            assert (
                                "Hits:" in keepa_text
                                and "Misses:" in keepa_text
                                and "Hit Ratio:" in keepa_text
                            )

                        if await ebay_cache.count() > 0:
                            ebay_text = await ebay_cache.text_content()
                            print(f"SUCCESS: eBay cache metrics: {ebay_text}")
                            # Verify hits/misses/hit ratio format
                            assert (
                                "Hits:" in ebay_text
                                and "Misses:" in ebay_text
                                and "Hit Ratio:" in ebay_text
                            )
                    else:
                        print(
                            "INFO: Cache Metrics section not displayed (no cache_stats in mock)"
                        )

                    # Check for Copy Report Path button when markdown_path is present
                    copy_button = page.get_by_test_id("copy-report-path")
                    if await copy_button.count() > 0:
                        copy_button_text = await copy_button.text_content()
                        print(
                            f"SUCCESS: Copy Report Path button detected: {copy_button_text}"
                        )

                        # Test the copy functionality
                        await copy_button.click()

                        # Wait for the "Copied!" feedback
                        await page.wait_for_function(
                            "() => document.querySelector('[data-testid=\"copy-report-path\"]').textContent.includes('Copied!')",
                            timeout=3000,
                        )

                        # Verify button shows "Copied!" feedback
                        feedback_text = await copy_button.text_content()
                        assert (
                            "Copied!" in feedback_text
                        ), f"Expected 'Copied!' feedback, got: {feedback_text}"
                        print("SUCCESS: Copy button feedback working correctly")

                        # Wait for text to reset back to original
                        await page.wait_for_function(
                            "() => document.querySelector('[data-testid=\"copy-report-path\"]').textContent === 'Copy Report Path'",
                            timeout=3000,
                        )

                        reset_text = await copy_button.text_content()
                        assert (
                            reset_text == "Copy Report Path"
                        ), f"Expected text to reset, got: {reset_text}"
                        print("SUCCESS: Copy button text reset working correctly")
                    else:
                        print(
                            "INFO: Copy Report Path button not displayed (no markdown_path in mock)"
                        )

            except Exception as e:
                print(f"Error checking results summary: {e}")
                print("Results summary not found or not visible")

            # Take a screenshot for debugging
            screenshot_path = Path("C:/Users/Husse/lot-genius/e2e_test_result.png")
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"Screenshot saved to: {screenshot_path}")

            # Verify that we detected key phases
            required_phases = {
                "start",
                "parse",
                "evidence",
            }  # Key phases that must be present
            missing_phases = required_phases - detected_phases
            assert (
                not missing_phases
            ), f"Missing required phases: {missing_phases}. Detected: {detected_phases}"

        except Exception as e:
            # Take screenshot on failure
            try:
                screenshot_path = Path("C:/Users/Husse/lot-genius/e2e_test_failure.png")
                await page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"Failure screenshot saved to: {screenshot_path}")
            except:
                pass
            raise e

        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_frontend_ui_elements():
    """Test that all required UI elements are present and functional."""

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        pytest.skip("Playwright not installed")

    # Read frontend URL from environment
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3002")

    # Preflight check
    if not check_frontend_running(frontend_url):
        pytest.skip(f"Frontend not running at {frontend_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(frontend_url)

            # Check main title
            title_element = await page.wait_for_selector(
                "h1:has-text('Lot Genius')", timeout=5000
            )
            assert title_element is not None

            # Switch to SSE tab
            sse_tab = page.get_by_text("Pipeline (SSE)")
            await sse_tab.click()

            # Check UI elements using data-testids
            file_input = page.get_by_test_id("file-input")
            assert await file_input.count() == 1

            run_button = page.get_by_test_id("run-pipeline")
            assert await run_button.count() == 1

            sse_console = page.get_by_test_id("sse-console")
            assert await sse_console.count() == 1

            # Check that button is initially disabled
            button_disabled = await run_button.get_attribute("disabled")
            assert button_disabled is not None

            # Check direct backend toggle
            backend_toggle = page.get_by_test_id("toggle-direct-backend")
            assert await backend_toggle.count() == 1

            print("SUCCESS: All UI elements found with correct data-testids")

        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_file_upload_validation():
    """Test file upload validation and UI feedback."""

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        pytest.skip("Playwright not installed")

    # Read frontend URL from environment
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3002")

    # Preflight check
    if not check_frontend_running(frontend_url):
        pytest.skip(f"Frontend not running at {frontend_url}")

    test_manifest_path = Path("C:/Users/Husse/lot-genius/test_manifest.csv")
    assert test_manifest_path.exists()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(frontend_url)

            # Switch to SSE tab
            sse_tab = page.get_by_text("Pipeline (SSE)")
            await sse_tab.click()

            # Initially button should be disabled
            run_button = page.get_by_test_id("run-pipeline")
            assert await run_button.get_attribute("disabled") is not None

            # Upload file using data-testid
            file_input = page.get_by_test_id("file-input")
            await file_input.set_input_files(str(test_manifest_path))

            # Wait for UI to update and button to be enabled
            await page.wait_for_function(
                "() => !document.querySelector('[data-testid=\"run-pipeline\"]').disabled",
                timeout=5000,
            )

            # Verify button is now clickable
            button_disabled = await run_button.get_attribute("disabled")
            assert button_disabled is None

            print("SUCCESS: File upload validation working correctly")

        finally:
            await browser.close()


if __name__ == "__main__":
    # Run the test directly if executed as script
    asyncio.run(test_complete_pipeline_e2e())
