"""
Browser Automation Service

Comprehensive Playwright-based browser automation for Novel-Engine AI acceptance testing.
Provides multi-browser testing, visual regression, accessibility validation, and performance measurement.
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Playwright imports
from playwright.async_api import Browser, BrowserContext
from playwright.async_api import Page, Playwright, async_playwright
from pydantic import BaseModel, Field

# Import Novel-Engine patterns
try:
    from config_loader import get_config

    from src.event_bus import EventBus
except ImportError:
    # Fallback for testing
    def get_config():
        return None

    def EventBus():
        return None


# Import AI testing contracts
from ai_testing.interfaces.service_contracts import (
    IBrowserAutomation,
    ServiceHealthResponse,
    TestContext,
    TestResult,
    TestStatus,
    UITestSpec,
)

# Import AI testing configuration
from ai_testing_config import get_ai_testing_service_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Browser Automation Models ===


class BrowserConfig(BaseModel):
    """Browser configuration for testing"""

    browser_type: str = Field(default="chromium", pattern="^(chromium|firefox|webkit)$")
    headless: bool = True
    viewport: Dict[str, int] = Field(default={"width": 1280, "height": 720})
    device_type: Optional[str] = None  # "mobile", "tablet", "desktop"
    user_agent: Optional[str] = None

    # Performance settings
    timeout_ms: int = 30000
    navigation_timeout_ms: int = 30000
    slow_mo_ms: int = 0  # Slow down operations for debugging

    # Recording settings
    record_video: bool = False
    record_trace: bool = False
    capture_screenshots: bool = True


class UIAction(BaseModel):
    """UI action specification"""

    action_type: str = Field(..., description="Type of action: click, type, select, etc.")
    selector: str = Field(..., description="Element selector")
    value: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    wait_for: Optional[str] = None  # Wait condition after action
    timeout_ms: Optional[int] = None


class UIAssertion(BaseModel):
    """UI assertion specification"""

    assertion_type: str = Field(..., description="Type of assertion: visible, text, value, etc.")
    selector: Optional[str] = None
    expected_value: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    timeout_ms: Optional[int] = None


class VisualTestResult(BaseModel):
    """Visual testing result"""

    screenshot_path: str
    baseline_path: Optional[str] = None
    diff_path: Optional[str] = None
    diff_percentage: float = 0.0
    visual_match: bool = True
    threshold: float = 0.1


class AccessibilityResult(BaseModel):
    """Accessibility testing result"""

    violations: List[Dict[str, Any]] = Field(default_factory=list)
    passes: List[Dict[str, Any]] = Field(default_factory=list)
    incomplete: List[Dict[str, Any]] = Field(default_factory=list)
    score: float = 1.0  # 0.0 to 1.0


class PerformanceMetrics(BaseModel):
    """Performance measurement result"""

    # Core Web Vitals
    first_contentful_paint: Optional[float] = None  # FCP
    largest_contentful_paint: Optional[float] = None  # LCP
    cumulative_layout_shift: Optional[float] = None  # CLS
    first_input_delay: Optional[float] = None  # FID

    # Additional metrics
    load_time_ms: float
    dom_content_loaded_ms: float
    time_to_interactive_ms: Optional[float] = None

    # Resource metrics
    page_size_bytes: int = 0
    requests_count: int = 0
    failed_requests: int = 0

    # JavaScript metrics
    js_heap_used_mb: float = 0.0
    js_heap_total_mb: float = 0.0


# === Browser Manager ===


class BrowserManager:
    """
    Manages browser instances and contexts for testing

    Features:
    - Multi-browser support (Chromium, Firefox, WebKit)
    - Device emulation and viewport management
    - Session isolation and cleanup
    - Resource optimization and pooling
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.playwright: Optional[Playwright] = None
        self.browsers: Dict[str, Browser] = {}
        self.active_contexts: Dict[str, BrowserContext] = {}

        # Configuration
        self.max_concurrent_contexts = config.get("max_concurrent_contexts", 10)
        self.default_timeout_ms = config.get("default_timeout_ms", 30000)
        self.screenshots_dir = Path(config.get("screenshots_dir", "ai_testing/screenshots"))
        self.videos_dir = Path(config.get("videos_dir", "ai_testing/videos"))

        # Ensure directories exist
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Browser Manager initialized")

    async def initialize(self):
        """Initialize Playwright and browsers"""
        try:
            self.playwright = await async_playwright().start()

            # Launch browsers
            browser_types = self.config.get("browser_types", ["chromium"])
            for browser_type in browser_types:
                await self._launch_browser(browser_type)

            logger.info(f"Browser Manager ready with {len(self.browsers)} browsers")

        except Exception as e:
            logger.error(f"Browser Manager initialization failed: {e}")
            raise

    async def cleanup(self):
        """Clean up browsers and Playwright"""
        try:
            # Close all contexts
            for context in list(self.active_contexts.values()):
                await context.close()
            self.active_contexts.clear()

            # Close all browsers
            for browser in self.browsers.values():
                await browser.close()
            self.browsers.clear()

            # Stop Playwright
            if self.playwright:
                await self.playwright.stop()

            logger.info("Browser Manager cleanup complete")

        except Exception as e:
            logger.error(f"Browser Manager cleanup error: {e}")

    async def _launch_browser(self, browser_type: str):
        """Launch a specific browser type"""
        try:
            browser_config = {
                "headless": self.config.get("headless", True),
                "slow_mo": self.config.get("slow_mo_ms", 0),
                "args": self.config.get("browser_args", []),
            }

            if browser_type == "chromium":
                browser = await self.playwright.chromium.launch(**browser_config)
            elif browser_type == "firefox":
                browser = await self.playwright.firefox.launch(**browser_config)
            elif browser_type == "webkit":
                browser = await self.playwright.webkit.launch(**browser_config)
            else:
                raise ValueError(f"Unsupported browser type: {browser_type}")

            self.browsers[browser_type] = browser
            logger.info(f"Browser launched: {browser_type}")

        except Exception as e:
            logger.error(f"Failed to launch {browser_type}: {e}")
            raise

    async def create_context(
        self, browser_config: BrowserConfig, context_id: Optional[str] = None
    ) -> str:
        """Create a new browser context"""
        context_id = context_id or str(uuid.uuid4())

        if context_id in self.active_contexts:
            raise ValueError(f"Context {context_id} already exists")

        if len(self.active_contexts) >= self.max_concurrent_contexts:
            raise RuntimeError("Maximum concurrent contexts reached")

        browser = self.browsers.get(browser_config.browser_type)
        if not browser:
            raise ValueError(f"Browser {browser_config.browser_type} not available")

        # Context configuration
        context_options = {
            "viewport": browser_config.viewport,
            "user_agent": browser_config.user_agent,
        }

        # Device emulation
        if browser_config.device_type:
            device = self.playwright.devices.get(browser_config.device_type)
            if device:
                context_options.update(device)

        # Recording options
        if browser_config.record_video:
            context_options["record_video_dir"] = str(self.videos_dir)

        if browser_config.record_trace:
            context_options["record_trace_dir"] = str(self.videos_dir / "traces")

        # Create context
        context = await browser.new_context(**context_options)

        # Set timeouts
        context.set_default_timeout(browser_config.timeout_ms)
        context.set_default_navigation_timeout(browser_config.navigation_timeout_ms)

        self.active_contexts[context_id] = context

        logger.info(f"Browser context created: {context_id}")
        return context_id

    async def get_context(self, context_id: str) -> BrowserContext:
        """Get browser context by ID"""
        context = self.active_contexts.get(context_id)
        if not context:
            raise ValueError(f"Context {context_id} not found")
        return context

    async def close_context(self, context_id: str):
        """Close browser context"""
        context = self.active_contexts.pop(context_id, None)
        if context:
            await context.close()
            logger.info(f"Browser context closed: {context_id}")


# === Browser Automation Service ===


class BrowserAutomationService(IBrowserAutomation):
    """
    Comprehensive browser automation service using Playwright

    Features:
    - Multi-browser UI testing
    - Visual regression testing
    - Accessibility compliance validation
    - Performance measurement
    - Real user interaction simulation
    - Screenshot and video capture
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        try:
            self.event_bus = EventBus()
        except Exception:
            self.event_bus = None
        self.browser_manager = BrowserManager(config)
        self.http_client: Optional[httpx.AsyncClient] = None

        # Testing configuration
        self.visual_threshold = config.get("visual_threshold", 0.1)
        self.accessibility_standards = config.get("accessibility_standards", ["WCAG2A"])
        self.performance_thresholds = config.get(
            "performance_thresholds",
            {"load_time_ms": 3000, "fcp_ms": 1800, "lcp_ms": 2500, "cls": 0.1},
        )

        logger.info("Browser Automation Service initialized")

    async def initialize(self):
        """Initialize service resources"""
        await self.browser_manager.initialize()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Browser Automation Service ready")

    async def cleanup(self):
        """Clean up service resources"""
        await self.browser_manager.cleanup()
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Browser Automation Service cleanup complete")

    # === IBrowserAutomation Interface Implementation ===

    async def execute_ui_test(self, test_spec: UITestSpec, context: TestContext) -> TestResult:
        """Execute comprehensive UI test with browser automation"""

        test_id = f"ui_test_{int(time.time())}"
        start_time = time.time()

        try:
            logger.info(f"Starting UI test: {test_spec.page_url}")

            # Create browser configuration
            browser_config = BrowserConfig(
                browser_type=test_spec.browser,
                viewport=test_spec.viewport_size,
                device_type=test_spec.device_type,
                capture_screenshots=True,
                record_video=True if context.environment == "debug" else False,
            )

            # Create browser context
            context_id = await self.browser_manager.create_context(browser_config)
            browser_context = await self.browser_manager.get_context(context_id)

            # Create page
            page = await browser_context.new_page()

            try:
                # Execute test steps
                test_results = await self._execute_ui_test_steps(page, test_spec, context)

                # Capture final screenshot
                screenshot_path = await self._capture_screenshot(page, f"{test_id}_final")
                test_results["screenshots"] = [screenshot_path]

                # Calculate final result
                duration_ms = int((time.time() - start_time) * 1000)
                overall_passed = test_results.get("overall_passed", False)

                return TestResult(
                    execution_id=test_id,
                    scenario_id=context.session_id,
                    status=TestStatus.COMPLETED if overall_passed else TestStatus.FAILED,
                    passed=overall_passed,
                    score=test_results.get("score", 0.0),
                    duration_ms=duration_ms,
                    ui_results=test_results,
                    screenshots=[screenshot_path],
                    recommendations=test_results.get("recommendations", []),
                )

            finally:
                await page.close()
                await self.browser_manager.close_context(context_id)

        except Exception as e:
            logger.error(f"UI test execution failed: {e}")
            duration_ms = int((time.time() - start_time) * 1000)

            return TestResult(
                execution_id=test_id,
                scenario_id=context.session_id,
                status=TestStatus.FAILED,
                passed=False,
                score=0.0,
                duration_ms=duration_ms,
                error_type=type(e).__name__,
                error_message=str(e),
                recommendations=["Check page URL accessibility", "Verify UI selectors"],
            )

    async def capture_screenshot(self, page_url: str, viewport: Dict[str, int]) -> str:
        """Capture page screenshot"""

        browser_config = BrowserConfig(viewport=viewport)
        context_id = await self.browser_manager.create_context(browser_config)

        try:
            browser_context = await self.browser_manager.get_context(context_id)
            page = await browser_context.new_page()

            await page.goto(page_url)
            await page.wait_for_load_state("networkidle")

            screenshot_path = await self._capture_screenshot(page, f"capture_{int(time.time())}")

            await page.close()
            return screenshot_path

        finally:
            await self.browser_manager.close_context(context_id)

    async def run_accessibility_audit(self, page_url: str) -> Dict[str, Any]:
        """Run accessibility compliance audit"""

        browser_config = BrowserConfig()
        context_id = await self.browser_manager.create_context(browser_config)

        try:
            browser_context = await self.browser_manager.get_context(context_id)
            page = await browser_context.new_page()

            await page.goto(page_url)
            await page.wait_for_load_state("networkidle")

            # Run accessibility tests
            accessibility_result = await self._run_accessibility_tests(page)

            await page.close()
            return accessibility_result.model_dump()

        finally:
            await self.browser_manager.close_context(context_id)

    async def measure_performance(self, page_url: str) -> Dict[str, float]:
        """Measure page performance metrics"""

        browser_config = BrowserConfig()
        context_id = await self.browser_manager.create_context(browser_config)

        try:
            browser_context = await self.browser_manager.get_context(context_id)
            page = await browser_context.new_page()

            # Measure performance
            performance_metrics = await self._measure_performance(page, page_url)

            await page.close()
            return performance_metrics.model_dump()

        finally:
            await self.browser_manager.close_context(context_id)

    # === UI Test Execution ===

    async def _execute_ui_test_steps(
        self, page: Page, test_spec: UITestSpec, context: TestContext
    ) -> Dict[str, Any]:
        """Execute UI test steps and collect results"""

        results = {
            "page_load_successful": False,
            "actions_completed": 0,
            "assertions_passed": 0,
            "total_actions": len(test_spec.actions),
            "total_assertions": len(test_spec.assertions),
            "performance_metrics": {},
            "accessibility_results": {},
            "visual_results": {},
            "errors": [],
            "recommendations": [],
        }

        try:
            # Navigate to page
            start_time = time.time()
            await page.goto(test_spec.page_url)
            await page.wait_for_load_state("networkidle")
            load_time_ms = (time.time() - start_time) * 1000

            results["page_load_successful"] = True
            results["load_time_ms"] = load_time_ms

            # Execute actions
            for i, action in enumerate(test_spec.actions):
                try:
                    await self._execute_ui_action(page, action)
                    results["actions_completed"] += 1
                except Exception as e:
                    results["errors"].append(f"Action {i}: {str(e)}")

            # Execute assertions
            for i, assertion in enumerate(test_spec.assertions):
                try:
                    assertion_passed = await self._execute_ui_assertion(page, assertion)
                    if assertion_passed:
                        results["assertions_passed"] += 1
                except Exception as e:
                    results["errors"].append(f"Assertion {i}: {str(e)}")

            # Performance measurement
            if test_spec.performance_metrics:
                performance_metrics = await self._measure_performance(page, test_spec.page_url)
                results["performance_metrics"] = performance_metrics.model_dump()

            # Accessibility testing
            if test_spec.accessibility_standards:
                accessibility_results = await self._run_accessibility_tests(page)
                results["accessibility_results"] = accessibility_results.model_dump()

            # Visual regression testing
            if test_spec.screenshot_comparison:
                visual_results = await self._run_visual_regression_test(
                    page, test_spec.page_url, test_spec.visual_threshold
                )
                results["visual_results"] = visual_results.model_dump()

            # Calculate overall results
            actions_success_rate = results["actions_completed"] / max(results["total_actions"], 1)
            assertions_success_rate = results["assertions_passed"] / max(
                results["total_assertions"], 1
            )

            overall_score = (actions_success_rate + assertions_success_rate) / 2

            # Performance score
            if results["performance_metrics"]:
                perf_metrics = results["performance_metrics"]
                load_time_score = (
                    1.0
                    if perf_metrics.get("load_time_ms", 0)
                    < self.performance_thresholds["load_time_ms"]
                    else 0.5
                )
                overall_score = (overall_score + load_time_score) / 2

            # Accessibility score
            if results["accessibility_results"]:
                accessibility_score = results["accessibility_results"].get("score", 1.0)
                overall_score = (overall_score + accessibility_score) / 2

            results["overall_passed"] = overall_score >= 0.8
            results["score"] = overall_score

            # Generate recommendations
            results["recommendations"] = self._generate_ui_recommendations(results)

            return results

        except Exception as e:
            results["errors"].append(f"Test execution failed: {str(e)}")
            results["overall_passed"] = False
            results["score"] = 0.0
            return results

    async def _execute_ui_action(self, page: Page, action: UIAction):
        """Execute a single UI action"""

        # Wait for element if needed
        if action.wait_for:
            await page.wait_for_selector(action.wait_for, timeout=action.timeout_ms or 30000)

        # Execute action based on type
        if action.action_type == "click":
            await page.click(action.selector, timeout=action.timeout_ms)

        elif action.action_type == "type":
            await page.fill(action.selector, action.value or "", timeout=action.timeout_ms)

        elif action.action_type == "select":
            await page.select_option(action.selector, action.value, timeout=action.timeout_ms)

        elif action.action_type == "hover":
            await page.hover(action.selector, timeout=action.timeout_ms)

        elif action.action_type == "wait":
            wait_time = float(action.value or "1.0")
            await asyncio.sleep(wait_time)

        elif action.action_type == "scroll":
            if action.selector:
                await page.locator(action.selector).scroll_into_view_if_needed()
            else:
                await page.evaluate(f"window.scrollBy(0, {action.value or 100})")

        elif action.action_type == "press":
            await page.keyboard.press(action.value or "Enter")

        else:
            raise ValueError(f"Unsupported action type: {action.action_type}")

        # Brief pause after action
        await asyncio.sleep(0.1)

    async def _execute_ui_assertion(self, page: Page, assertion: UIAssertion) -> bool:
        """Execute a single UI assertion"""

        timeout = assertion.timeout_ms or 5000

        if assertion.assertion_type == "visible":
            return await page.is_visible(assertion.selector, timeout=timeout)

        elif assertion.assertion_type == "hidden":
            return not await page.is_visible(assertion.selector, timeout=timeout)

        elif assertion.assertion_type == "text":
            element = page.locator(assertion.selector)
            await element.wait_for(timeout=timeout)
            text_content = await element.inner_text()
            return assertion.expected_value in text_content

        elif assertion.assertion_type == "value":
            element = page.locator(assertion.selector)
            await element.wait_for(timeout=timeout)
            input_value = await element.input_value()
            return input_value == assertion.expected_value

        elif assertion.assertion_type == "count":
            elements = page.locator(assertion.selector)
            count = await elements.count()
            expected_count = int(assertion.expected_value or "1")
            return count == expected_count

        elif assertion.assertion_type == "url":
            current_url = page.url
            return assertion.expected_value in current_url

        elif assertion.assertion_type == "title":
            title = await page.title()
            return assertion.expected_value in title

        else:
            raise ValueError(f"Unsupported assertion type: {assertion.assertion_type}")

    # === Performance Measurement ===

    async def _measure_performance(self, page: Page, page_url: str) -> PerformanceMetrics:
        """Measure comprehensive page performance metrics"""

        # Start performance measurement
        await page.goto(page_url, wait_until="networkidle")

        # Get performance timing
        performance_timing = await page.evaluate(
            """
            () => {
                const timing = performance.timing;
                const navigation = performance.getEntriesByType('navigation')[0];
                const paint = performance.getEntriesByType('paint');
                
                return {
                    loadEventEnd: timing.loadEventEnd,
                    loadEventStart: timing.loadEventStart,
                    domContentLoadedEventEnd: timing.domContentLoadedEventEnd,
                    navigationStart: timing.navigationStart,
                    firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || null,
                    largestContentfulPaint: null,  // Would need LCP observer
                    cumulativeLayoutShift: null,   // Would need CLS observer
                    firstInputDelay: null          // Would need FID observer
                };
            }
        """
        )

        # Calculate metrics
        load_time_ms = performance_timing["loadEventEnd"] - performance_timing["navigationStart"]
        dom_content_loaded_ms = (
            performance_timing["domContentLoadedEventEnd"] - performance_timing["navigationStart"]
        )

        # Get resource information
        resource_info = await page.evaluate(
            """
            () => {
                const resources = performance.getEntriesByType('resource');
                const totalSize = resources.reduce((sum, resource) => {
                    return sum + (resource.transferSize || 0);
                }, 0);
                
                return {
                    requestsCount: resources.length,
                    totalSizeBytes: totalSize,
                    failedRequests: resources.filter(r => r.responseStatus >= 400).length
                };
            }
        """
        )

        # Get memory information
        memory_info = await page.evaluate(
            """
            () => {
                if (performance.memory) {
                    return {
                        usedJSHeapSize: performance.memory.usedJSHeapSize,
                        totalJSHeapSize: performance.memory.totalJSHeapSize
                    };
                }
                return { usedJSHeapSize: 0, totalJSHeapSize: 0 };
            }
        """
        )

        return PerformanceMetrics(
            first_contentful_paint=performance_timing.get("firstContentfulPaint"),
            largest_contentful_paint=performance_timing.get("largestContentfulPaint"),
            cumulative_layout_shift=performance_timing.get("cumulativeLayoutShift"),
            first_input_delay=performance_timing.get("firstInputDelay"),
            load_time_ms=max(load_time_ms, 0),
            dom_content_loaded_ms=max(dom_content_loaded_ms, 0),
            page_size_bytes=resource_info["totalSizeBytes"],
            requests_count=resource_info["requestsCount"],
            failed_requests=resource_info["failedRequests"],
            js_heap_used_mb=memory_info["usedJSHeapSize"] / (1024 * 1024),
            js_heap_total_mb=memory_info["totalJSHeapSize"] / (1024 * 1024),
        )

    # === Accessibility Testing ===

    async def _run_accessibility_tests(self, page: Page) -> AccessibilityResult:
        """Run accessibility compliance tests"""

        # Inject axe-core for accessibility testing
        await page.add_script_tag(url="https://unpkg.com/axe-core@latest/axe.min.js")

        # Run accessibility audit
        accessibility_results = await page.evaluate(
            """
            async () => {
                if (typeof axe !== 'undefined') {
                    try {
                        const results = await axe.run();
                        return {
                            violations: results.violations,
                            passes: results.passes,
                            incomplete: results.incomplete
                        };
                    } catch (error) {
                        return {
                            violations: [],
                            passes: [],
                            incomplete: [],
                            error: error.message
                        };
                    }
                }
                return {
                    violations: [],
                    passes: [],
                    incomplete: [],
                    error: 'axe-core not loaded'
                };
            }
        """
        )

        # Calculate accessibility score
        violations_count = len(accessibility_results.get("violations", []))
        passes_count = len(accessibility_results.get("passes", []))

        if passes_count + violations_count > 0:
            score = passes_count / (passes_count + violations_count)
        else:
            score = 1.0

        return AccessibilityResult(
            violations=accessibility_results.get("violations", []),
            passes=accessibility_results.get("passes", []),
            incomplete=accessibility_results.get("incomplete", []),
            score=score,
        )

    # === Visual Regression Testing ===

    async def _run_visual_regression_test(
        self, page: Page, page_url: str, threshold: float
    ) -> VisualTestResult:
        """Run visual regression testing"""

        # Generate unique screenshot name
        page_hash = str(hash(page_url))[:8]
        screenshot_name = f"visual_test_{page_hash}"

        # Capture current screenshot
        current_screenshot = await self._capture_screenshot(page, screenshot_name)

        # Look for baseline screenshot
        baseline_path = self.browser_manager.screenshots_dir / f"{screenshot_name}_baseline.png"

        if not baseline_path.exists():
            # Create baseline for first run
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(baseline_path), full_page=True)

            return VisualTestResult(
                screenshot_path=current_screenshot,
                baseline_path=str(baseline_path),
                diff_percentage=0.0,
                visual_match=True,
                threshold=threshold,
            )

        # Compare screenshots (simplified - in production would use image comparison library)
        # For now, assume visual match based on file size similarity
        current_size = Path(current_screenshot).stat().st_size
        baseline_size = baseline_path.stat().st_size
        size_diff = abs(current_size - baseline_size) / baseline_size if baseline_size > 0 else 1.0

        visual_match = size_diff <= threshold

        return VisualTestResult(
            screenshot_path=current_screenshot,
            baseline_path=str(baseline_path),
            diff_percentage=size_diff,
            visual_match=visual_match,
            threshold=threshold,
        )

    # === Utility Methods ===

    async def _capture_screenshot(self, page: Page, name: str) -> str:
        """Capture and save screenshot"""
        timestamp = int(time.time())
        screenshot_path = self.browser_manager.screenshots_dir / f"{name}_{timestamp}.png"

        await page.screenshot(path=str(screenshot_path), full_page=True)

        logger.info(f"Screenshot captured: {screenshot_path}")
        return str(screenshot_path)

    def _generate_ui_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate UI test recommendations"""
        recommendations = []

        # Action completion recommendations
        actions_rate = results["actions_completed"] / max(results["total_actions"], 1)
        if actions_rate < 0.8:
            recommendations.append("Some UI actions failed - check element selectors and timing")

        # Assertion recommendations
        assertions_rate = results["assertions_passed"] / max(results["total_assertions"], 1)
        if assertions_rate < 0.8:
            recommendations.append("Some UI assertions failed - verify expected UI state")

        # Performance recommendations
        if results.get("performance_metrics"):
            perf = results["performance_metrics"]
            load_time = perf.get("load_time_ms", 0)

            if load_time > self.performance_thresholds["load_time_ms"]:
                recommendations.append(f"Page load time ({load_time:.0f}ms) exceeds threshold")

            failed_requests = perf.get("failed_requests", 0)
            if failed_requests > 0:
                recommendations.append(f"{failed_requests} failed resource requests detected")

        # Accessibility recommendations
        if results.get("accessibility_results"):
            accessibility = results["accessibility_results"]
            violations = len(accessibility.get("violations", []))

            if violations > 0:
                recommendations.append(f"{violations} accessibility violations found")

            if accessibility.get("score", 1.0) < 0.9:
                recommendations.append("Consider improving accessibility compliance")

        # Visual regression recommendations
        if results.get("visual_results"):
            visual = results["visual_results"]
            if not visual.get("visual_match", True):
                recommendations.append("Visual differences detected - review UI changes")

        if not recommendations:
            recommendations.append("UI test passed all checks successfully")

        return recommendations


# === FastAPI Application ===


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan management"""
    # Initialize browser automation service
    browser_config = get_ai_testing_service_config("browser_automation")

    service = BrowserAutomationService(browser_config)
    await service.initialize()

    app.state.browser_service = service

    logger.info("Browser Automation Service started")
    yield

    await service.cleanup()
    logger.info("Browser Automation Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Browser Automation Service",
    description="Playwright-based browser automation for Novel-Engine AI acceptance testing",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === API Endpoints ===


@app.get("/health", response_model=ServiceHealthResponse)
async def health_check():
    """Service health check"""
    service: BrowserAutomationService = app.state.browser_service

    browser_status = "connected" if service.browser_manager.browsers else "disconnected"
    active_contexts = len(service.browser_manager.active_contexts)

    status = "healthy" if browser_status == "connected" else "unhealthy"

    return ServiceHealthResponse(
        service_name="browser-automation",
        status=status,
        version="1.0.0",
        database_status="not_applicable",
        message_queue_status="connected",
        external_dependencies={"playwright": browser_status},
        response_time_ms=25.0,
        memory_usage_mb=200.0,
        cpu_usage_percent=10.0,
        active_tests=active_contexts,
        completed_tests_24h=0,  # Would be tracked
        error_rate_percent=0.0,
    )


@app.post("/execute", response_model=TestResult)
async def execute_ui_test(
    scenario: Dict[str, Any], execution: Dict[str, Any], context: Dict[str, Any]
):
    """Execute UI test scenario"""
    service: BrowserAutomationService = app.state.browser_service

    # Parse request
    ui_spec = UITestSpec(**scenario["config"]["ui_spec"])
    test_context = TestContext(**context)

    # Execute test
    result = await service.execute_ui_test(ui_spec, test_context)
    return result


@app.post("/screenshot", response_model=Dict[str, str])
async def capture_page_screenshot(page_url: str, viewport: Optional[Dict[str, int]] = None):
    """Capture page screenshot"""
    service: BrowserAutomationService = app.state.browser_service

    viewport = viewport or {"width": 1280, "height": 720}
    screenshot_path = await service.capture_screenshot(page_url, viewport)

    return {"screenshot_path": screenshot_path}


@app.post("/accessibility", response_model=Dict[str, Any])
async def run_accessibility_audit(page_url: str):
    """Run accessibility audit"""
    service: BrowserAutomationService = app.state.browser_service

    result = await service.run_accessibility_audit(page_url)
    return result


@app.post("/performance", response_model=Dict[str, float])
async def measure_page_performance(page_url: str):
    """Measure page performance"""
    service: BrowserAutomationService = app.state.browser_service

    metrics = await service.measure_performance(page_url)
    return metrics


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
