"""
Accessibility and Performance Testing Integration

Advanced accessibility compliance and performance measurement framework
for Novel-Engine AI acceptance testing with WCAG compliance and Core Web Vitals.
"""

import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# Import AI testing contracts
from ai_testing.interfaces.service_contracts import (
    QualityMetric,
    TestContext,
)

# Import Novel-Engine patterns
from playwright.async_api import Page


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Accessibility Models ===


class WCAGLevel(str, Enum):
    """WCAG compliance levels"""

    A = "A"
    AA = "AA"
    AAA = "AAA"


class AccessibilityViolation(dict):
    """Accessibility violation with details"""

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self.id = data.get("id", "")
        self.impact = data.get("impact", "minor")
        self.description = data.get("description", "")
        self.help = data.get("help", "")
        self.help_url = data.get("helpUrl", "")
        self.nodes = data.get("nodes", [])

    @property
    def severity_score(self) -> float:
        """Get numerical severity score"""
        severity_map = {"minor": 0.25, "moderate": 0.5, "serious": 0.75, "critical": 1.0}
        return severity_map.get(self.impact, 0.5)


@dataclass
class AccessibilityTestResult:
    """Comprehensive accessibility test result"""

    wcag_level: WCAGLevel
    overall_score: float
    violations: List[AccessibilityViolation] = field(default_factory=list)
    passes: List[Dict[str, Any]] = field(default_factory=list)
    incomplete: List[Dict[str, Any]] = field(default_factory=list)

    # Category scores
    perceivable_score: float = 1.0
    operable_score: float = 1.0
    understandable_score: float = 1.0
    robust_score: float = 1.0

    # Detailed metrics
    color_contrast_issues: int = 0
    keyboard_navigation_issues: int = 0
    screen_reader_issues: int = 0
    focus_management_issues: int = 0

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    priority_fixes: List[str] = field(default_factory=list)


# === Performance Models ===


@dataclass
class CoreWebVitals:
    """Core Web Vitals measurements"""

    # Loading performance
    largest_contentful_paint: Optional[float] = None  # LCP - should be < 2.5s
    first_contentful_paint: Optional[float] = None  # FCP - should be < 1.8s

    # Interactivity
    first_input_delay: Optional[float] = None  # FID - should be < 100ms
    total_blocking_time: Optional[float] = None  # TBT

    # Visual stability
    cumulative_layout_shift: Optional[float] = None  # CLS - should be < 0.1

    def get_score(self) -> float:
        """Calculate overall Core Web Vitals score"""
        scores = []

        if self.largest_contentful_paint is not None:
            lcp_score = (
                1.0
                if self.largest_contentful_paint <= 2500
                else 0.5
                if self.largest_contentful_paint <= 4000
                else 0.0
            )
            scores.append(lcp_score)

        if self.first_contentful_paint is not None:
            fcp_score = (
                1.0
                if self.first_contentful_paint <= 1800
                else 0.5
                if self.first_contentful_paint <= 3000
                else 0.0
            )
            scores.append(fcp_score)

        if self.first_input_delay is not None:
            fid_score = (
                1.0
                if self.first_input_delay <= 100
                else 0.5
                if self.first_input_delay <= 300
                else 0.0
            )
            scores.append(fid_score)

        if self.cumulative_layout_shift is not None:
            cls_score = (
                1.0
                if self.cumulative_layout_shift <= 0.1
                else 0.5
                if self.cumulative_layout_shift <= 0.25
                else 0.0
            )
            scores.append(cls_score)

        return statistics.mean(scores) if scores else 0.0

    def get_performance_grade(self) -> str:
        """Get performance grade based on score"""
        score = self.get_score()
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"


@dataclass
class PerformanceTestResult:
    """Comprehensive performance test result"""

    core_web_vitals: CoreWebVitals
    overall_score: float

    # Additional metrics
    load_time_ms: float = 0.0
    dom_content_loaded_ms: float = 0.0
    time_to_interactive_ms: Optional[float] = None

    # Resource metrics
    total_requests: int = 0
    failed_requests: int = 0
    total_size_kb: float = 0.0
    image_size_kb: float = 0.0
    script_size_kb: float = 0.0
    style_size_kb: float = 0.0

    # Memory metrics
    js_heap_used_mb: float = 0.0
    js_heap_total_mb: float = 0.0

    # Network metrics
    bandwidth_estimate_mbps: Optional[float] = None
    effective_connection_type: Optional[str] = None

    # Performance insights
    opportunities: List[str] = field(default_factory=list)
    diagnostics: List[str] = field(default_factory=list)

    def get_lighthouse_score(self) -> int:
        """Calculate Lighthouse-style performance score (0-100)"""
        return int(self.overall_score * 100)


# === Accessibility Testing Framework ===


class AccessibilityTester:
    """
    Comprehensive accessibility testing using axe-core and custom checks

    Features:
    - WCAG 2.1 A/AA/AAA compliance testing
    - Automated accessibility scanning
    - Keyboard navigation testing
    - Screen reader compatibility
    - Color contrast validation
    - Focus management assessment
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.wcag_level = WCAGLevel(config.get("wcag_level", "AA"))
        self.include_experimental = config.get("include_experimental", False)

        # Testing configuration
        self.keyboard_test_timeout = config.get("keyboard_test_timeout", 5000)
        self.focus_indicators_required = config.get("focus_indicators_required", True)

        logger.info(f"Accessibility Tester initialized for WCAG {self.wcag_level}")

    async def run_comprehensive_accessibility_test(
        self, page: Page, context: TestContext
    ) -> AccessibilityTestResult:
        """Run comprehensive accessibility test suite"""

        try:
            # Inject axe-core
            await self._inject_axe_core(page)

            # Run automated accessibility scan
            axe_results = await self._run_axe_scan(page)

            # Run custom accessibility tests
            keyboard_results = await self._test_keyboard_navigation(page)
            focus_results = await self._test_focus_management(page)
            contrast_results = await self._test_color_contrast(page)

            # Process results
            result = await self._process_accessibility_results(
                axe_results, keyboard_results, focus_results, contrast_results
            )

            logger.info(f"Accessibility test completed with score: {result.overall_score:.2f}")
            return result

        except Exception as e:
            logger.error(f"Accessibility testing failed: {e}")
            return AccessibilityTestResult(
                wcag_level=self.wcag_level,
                overall_score=0.0,
                recommendations=["Accessibility testing failed - check page accessibility"],
            )

    async def _inject_axe_core(self, page: Page):
        """Inject axe-core library for accessibility testing"""
        try:
            await page.add_script_tag(url="https://unpkg.com/axe-core@latest/axe.min.js")

            # Wait for axe to be available
            await page.wait_for_function("typeof axe !== 'undefined'", timeout=10000)

        except Exception as e:
            logger.error(f"Failed to inject axe-core: {e}")
            raise

    async def _run_axe_scan(self, page: Page) -> Dict[str, Any]:
        """Run axe-core accessibility scan"""

        # Configure axe rules based on WCAG level
        axe_config = {
            "rules": {},
            "tags": [f"wcag{self.wcag_level.value.lower()}", "best-practice"],
        }

        if self.include_experimental:
            axe_config["tags"].append("experimental")

        # Run axe scan
        axe_results = await page.evaluate(
            f"""
            async () => {{
                try {{
                    const results = await axe.run(document, {json.dumps(axe_config)});
                    return {{
                        violations: results.violations,
                        passes: results.passes,
                        incomplete: results.incomplete,
                        timestamp: results.timestamp
                    }};
                }} catch (error) {{
                    return {{
                        violations: [],
                        passes: [],
                        incomplete: [],
                        error: error.message
                    }};
                }}
            }}
        """
        )

        return axe_results

    async def _test_keyboard_navigation(self, page: Page) -> Dict[str, Any]:
        """Test keyboard navigation functionality"""

        results = {
            "focusable_elements": 0,
            "keyboard_accessible": 0,
            "tab_order_logical": True,
            "skip_links_present": False,
            "keyboard_traps": 0,
            "focus_indicators": 0,
        }

        try:
            # Find all focusable elements
            focusable_elements = await page.evaluate(
                """
                () => {
                    const focusableSelectors = [
                        'a[href]', 'button', 'input', 'textarea', 'select',
                        '[tabindex]:not([tabindex="-1"])', '[contenteditable="true"]'
                    ];
                    
                    const elements = document.querySelectorAll(focusableSelectors.join(', '));
                    return Array.from(elements).map(el => ({
                        tagName: el.tagName,
                        type: el.type || '',
                        tabIndex: el.tabIndex,
                        id: el.id || '',
                        className: el.className || '',
                        visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
                    }));
                }
            """
            )

            results["focusable_elements"] = len(focusable_elements)

            # Test keyboard navigation
            if focusable_elements:
                # Start from beginning
                await page.keyboard.press("Tab")

                keyboard_accessible = 0
                focus_indicators = 0

                for i, element in enumerate(focusable_elements[:10]):  # Test first 10 elements
                    try:
                        # Check if element receives focus
                        focused_element = await page.evaluate("document.activeElement.tagName")
                        if focused_element:
                            keyboard_accessible += 1

                        # Check for focus indicator
                        has_focus_indicator = await page.evaluate(
                            """
                            () => {
                                const activeElement = document.activeElement;
                                const styles = window.getComputedStyle(activeElement);
                                return styles.outline !== 'none' || 
                                       styles.outlineWidth !== '0px' ||
                                       styles.boxShadow !== 'none';
                            }
                        """
                        )

                        if has_focus_indicator:
                            focus_indicators += 1

                        # Move to next element
                        await page.keyboard.press("Tab")
                        await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.warning(f"Keyboard navigation test error: {e}")

                results["keyboard_accessible"] = keyboard_accessible
                results["focus_indicators"] = focus_indicators

            # Check for skip links
            skip_links = await page.locator("a[href*='#']").filter(has_text="skip").count()
            results["skip_links_present"] = skip_links > 0

        except Exception as e:
            logger.error(f"Keyboard navigation testing failed: {e}")

        return results

    async def _test_focus_management(self, page: Page) -> Dict[str, Any]:
        """Test focus management and logical flow"""

        results = {
            "focus_management_score": 1.0,
            "logical_reading_order": True,
            "focus_visible": True,
            "no_focus_traps": True,
            "issues": [],
        }

        try:
            # Test focus visibility
            focus_visible_test = await page.evaluate(
                """
                () => {
                    // Create a temporary button to test focus
                    const testButton = document.createElement('button');
                    testButton.textContent = 'Test Focus';
                    testButton.style.position = 'absolute';
                    testButton.style.top = '-1000px';
                    document.body.appendChild(testButton);
                    
                    testButton.focus();
                    const styles = window.getComputedStyle(testButton);
                    const hasFocusIndicator = styles.outline !== 'none' || 
                                            styles.outlineWidth !== '0px';
                    
                    document.body.removeChild(testButton);
                    return hasFocusIndicator;
                }
            """
            )

            results["focus_visible"] = focus_visible_test
            if not focus_visible_test:
                results["issues"].append("Focus indicators may not be visible")

            # Test reading order
            heading_order_test = await page.evaluate(
                """
                () => {
                    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                    let previousLevel = 0;
                    let orderIssues = 0;
                    
                    headings.forEach(heading => {
                        const currentLevel = parseInt(heading.tagName.charAt(1));
                        if (currentLevel - previousLevel > 1) {
                            orderIssues++;
                        }
                        previousLevel = currentLevel;
                    });
                    
                    return { 
                        totalHeadings: headings.length,
                        orderIssues: orderIssues,
                        logicalOrder: orderIssues === 0
                    };
                }
            """
            )

            results["logical_reading_order"] = heading_order_test["logicalOrder"]
            if not heading_order_test["logicalOrder"]:
                results["issues"].append("Heading structure may not follow logical order")

            # Calculate overall focus management score
            focus_factors = [
                results["focus_visible"],
                results["logical_reading_order"],
                results["no_focus_traps"],
            ]

            results["focus_management_score"] = sum(focus_factors) / len(focus_factors)

        except Exception as e:
            logger.error(f"Focus management testing failed: {e}")
            results["focus_management_score"] = 0.0

        return results

    async def _test_color_contrast(self, page: Page) -> Dict[str, Any]:
        """Test color contrast compliance"""

        results = {
            "contrast_ratio_aa": 0,
            "contrast_ratio_aaa": 0,
            "total_text_elements": 0,
            "contrast_issues": [],
            "average_contrast": 0.0,
        }

        try:
            contrast_analysis = await page.evaluate(
                """
                () => {
                    const textElements = document.querySelectorAll('p, span, div, h1, h2, h3, h4, h5, h6, a, button, label');
                    const contrastResults = [];
                    
                    function getRGB(color) {
                        const match = color.match(/\\d+/g);
                        return match ? match.map(Number) : [0, 0, 0];
                    }
                    
                    function getLuminance(r, g, b) {
                        const [rs, gs, bs] = [r, g, b].map(c => {
                            c = c / 255;
                            return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
                        });
                        return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
                    }
                    
                    function getContrastRatio(color1, color2) {
                        const lum1 = getLuminance(...getRGB(color1));
                        const lum2 = getLuminance(...getRGB(color2));
                        const lighter = Math.max(lum1, lum2);
                        const darker = Math.min(lum1, lum2);
                        return (lighter + 0.05) / (darker + 0.05);
                    }
                    
                    textElements.forEach((element, index) => {
                        if (element.offsetWidth > 0 && element.offsetHeight > 0) {
                            const styles = window.getComputedStyle(element);
                            const textColor = styles.color;
                            const backgroundColor = styles.backgroundColor;
                            
                            // If background is transparent, try to find parent background
                            let bgColor = backgroundColor;
                            if (bgColor === 'rgba(0, 0, 0, 0)' || bgColor === 'transparent') {
                                let parent = element.parentElement;
                                while (parent && (bgColor === 'rgba(0, 0, 0, 0)' || bgColor === 'transparent')) {
                                    bgColor = window.getComputedStyle(parent).backgroundColor;
                                    parent = parent.parentElement;
                                }
                                if (bgColor === 'rgba(0, 0, 0, 0)' || bgColor === 'transparent') {
                                    bgColor = 'rgb(255, 255, 255)'; // Default to white
                                }
                            }
                            
                            const contrastRatio = getContrastRatio(textColor, bgColor);
                            const fontSize = parseFloat(styles.fontSize);
                            const fontWeight = styles.fontWeight;
                            
                            const isLargeText = fontSize >= 18 || (fontSize >= 14 && (fontWeight === 'bold' || parseInt(fontWeight) >= 700));
                            const aaThreshold = isLargeText ? 3.0 : 4.5;
                            const aaaThreshold = isLargeText ? 4.5 : 7.0;
                            
                            contrastResults.push({
                                element: element.tagName + (element.className ? '.' + element.className.split(' ')[0] : ''),
                                textColor,
                                backgroundColor: bgColor,
                                contrastRatio,
                                fontSize,
                                isLargeText,
                                passesAA: contrastRatio >= aaThreshold,
                                passesAAA: contrastRatio >= aaaThreshold
                            });
                        }
                    });
                    
                    return contrastResults;
                }
            """
            )

            results["total_text_elements"] = len(contrast_analysis)

            if contrast_analysis:
                aa_passing = sum(1 for result in contrast_analysis if result["passesAA"])
                aaa_passing = sum(1 for result in contrast_analysis if result["passesAAA"])

                results["contrast_ratio_aa"] = aa_passing / len(contrast_analysis)
                results["contrast_ratio_aaa"] = aaa_passing / len(contrast_analysis)

                # Calculate average contrast
                contrast_ratios = [result["contrastRatio"] for result in contrast_analysis]
                results["average_contrast"] = statistics.mean(contrast_ratios)

                # Identify contrast issues
                for result in contrast_analysis:
                    if not result["passesAA"]:
                        results["contrast_issues"].append(
                            {
                                "element": result["element"],
                                "contrast_ratio": result["contrastRatio"],
                                "required": 4.5 if not result["isLargeText"] else 3.0,
                                "text_color": result["textColor"],
                                "background_color": result["backgroundColor"],
                            }
                        )

        except Exception as e:
            logger.error(f"Color contrast testing failed: {e}")

        return results

    async def _process_accessibility_results(
        self,
        axe_results: Dict[str, Any],
        keyboard_results: Dict[str, Any],
        focus_results: Dict[str, Any],
        contrast_results: Dict[str, Any],
    ) -> AccessibilityTestResult:
        """Process and combine accessibility test results"""

        # Process axe violations
        violations = [AccessibilityViolation(v) for v in axe_results.get("violations", [])]
        passes = axe_results.get("passes", [])
        incomplete = axe_results.get("incomplete", [])

        # Calculate category scores
        perceivable_score = self._calculate_perceivable_score(violations, contrast_results)
        operable_score = self._calculate_operable_score(violations, keyboard_results)
        understandable_score = self._calculate_understandable_score(violations)
        robust_score = self._calculate_robust_score(violations)

        # Calculate overall score
        overall_score = statistics.mean(
            [perceivable_score, operable_score, understandable_score, robust_score]
        )

        # Generate recommendations
        recommendations = self._generate_accessibility_recommendations(
            violations, keyboard_results, focus_results, contrast_results
        )

        # Identify priority fixes
        priority_fixes = self._identify_priority_fixes(violations)

        return AccessibilityTestResult(
            wcag_level=self.wcag_level,
            overall_score=overall_score,
            violations=violations,
            passes=passes,
            incomplete=incomplete,
            perceivable_score=perceivable_score,
            operable_score=operable_score,
            understandable_score=understandable_score,
            robust_score=robust_score,
            color_contrast_issues=len(contrast_results.get("contrast_issues", [])),
            keyboard_navigation_issues=keyboard_results.get("focusable_elements", 0)
            - keyboard_results.get("keyboard_accessible", 0),
            screen_reader_issues=len(
                [v for v in violations if "screen reader" in v.description.lower()]
            ),
            focus_management_issues=len(focus_results.get("issues", [])),
            recommendations=recommendations,
            priority_fixes=priority_fixes,
        )

    def _calculate_perceivable_score(
        self, violations: List[AccessibilityViolation], contrast_results: Dict[str, Any]
    ) -> float:
        """Calculate perceivable principle score"""
        perceivable_violations = [
            v
            for v in violations
            if any(tag in ["color-contrast", "images", "multimedia"] for tag in v.get("tags", []))
        ]

        # Base score from violations
        violation_penalty = sum(v.severity_score for v in perceivable_violations) * 0.1
        base_score = max(0.0, 1.0 - violation_penalty)

        # Adjust for contrast testing
        if contrast_results.get("total_text_elements", 0) > 0:
            contrast_score = contrast_results.get("contrast_ratio_aa", 1.0)
            base_score = (base_score + contrast_score) / 2

        return base_score

    def _calculate_operable_score(
        self, violations: List[AccessibilityViolation], keyboard_results: Dict[str, Any]
    ) -> float:
        """Calculate operable principle score"""
        operable_violations = [
            v
            for v in violations
            if any(tag in ["keyboard", "focus", "timing"] for tag in v.get("tags", []))
        ]

        # Base score from violations
        violation_penalty = sum(v.severity_score for v in operable_violations) * 0.1
        base_score = max(0.0, 1.0 - violation_penalty)

        # Adjust for keyboard testing
        if keyboard_results.get("focusable_elements", 0) > 0:
            keyboard_score = (
                keyboard_results.get("keyboard_accessible", 0)
                / keyboard_results["focusable_elements"]
            )
            focus_score = (
                keyboard_results.get("focus_indicators", 0) / keyboard_results["focusable_elements"]
            )
            keyboard_overall = (keyboard_score + focus_score) / 2
            base_score = (base_score + keyboard_overall) / 2

        return base_score

    def _calculate_understandable_score(self, violations: List[AccessibilityViolation]) -> float:
        """Calculate understandable principle score"""
        understandable_violations = [
            v
            for v in violations
            if any(tag in ["forms", "navigation", "language"] for tag in v.get("tags", []))
        ]

        violation_penalty = sum(v.severity_score for v in understandable_violations) * 0.1
        return max(0.0, 1.0 - violation_penalty)

    def _calculate_robust_score(self, violations: List[AccessibilityViolation]) -> float:
        """Calculate robust principle score"""
        robust_violations = [
            v
            for v in violations
            if any(tag in ["parsing", "compatibility"] for tag in v.get("tags", []))
        ]

        violation_penalty = sum(v.severity_score for v in robust_violations) * 0.1
        return max(0.0, 1.0 - violation_penalty)

    def _generate_accessibility_recommendations(
        self,
        violations: List[AccessibilityViolation],
        keyboard_results: Dict[str, Any],
        focus_results: Dict[str, Any],
        contrast_results: Dict[str, Any],
    ) -> List[str]:
        """Generate accessibility recommendations"""
        recommendations = []

        # Violation-based recommendations
        critical_violations = [v for v in violations if v.impact == "critical"]
        if critical_violations:
            recommendations.append(
                f"Address {len(critical_violations)} critical accessibility violations immediately"
            )

        serious_violations = [v for v in violations if v.impact == "serious"]
        if serious_violations:
            recommendations.append(f"Fix {len(serious_violations)} serious accessibility issues")

        # Keyboard navigation recommendations
        if keyboard_results.get("focusable_elements", 0) > 0:
            keyboard_accessible = keyboard_results.get("keyboard_accessible", 0)
            if keyboard_accessible < keyboard_results["focusable_elements"]:
                recommendations.append(
                    "Improve keyboard accessibility for all interactive elements"
                )

            focus_indicators = keyboard_results.get("focus_indicators", 0)
            if focus_indicators < keyboard_results["focusable_elements"] * 0.8:
                recommendations.append("Add visible focus indicators to interactive elements")

        # Color contrast recommendations
        contrast_aa_ratio = contrast_results.get("contrast_ratio_aa", 1.0)
        if contrast_aa_ratio < 0.9:
            recommendations.append("Improve color contrast to meet WCAG AA standards")

        contrast_issues = len(contrast_results.get("contrast_issues", []))
        if contrast_issues > 0:
            recommendations.append(f"Fix {contrast_issues} color contrast issues")

        # Focus management recommendations
        focus_issues = focus_results.get("issues", [])
        for issue in focus_issues:
            recommendations.append(f"Focus management: {issue}")

        if not recommendations:
            recommendations.append("Accessibility testing passed - excellent compliance!")

        return recommendations

    def _identify_priority_fixes(self, violations: List[AccessibilityViolation]) -> List[str]:
        """Identify priority accessibility fixes"""
        priority_fixes = []

        # Sort by impact severity
        critical_violations = sorted(
            [v for v in violations if v.impact == "critical"],
            key=lambda x: len(x.nodes),
            reverse=True,
        )
        serious_violations = sorted(
            [v for v in violations if v.impact == "serious"],
            key=lambda x: len(x.nodes),
            reverse=True,
        )

        # Add top critical violations
        for violation in critical_violations[:3]:
            priority_fixes.append(f"CRITICAL: {violation.description}")

        # Add top serious violations
        for violation in serious_violations[:2]:
            priority_fixes.append(f"SERIOUS: {violation.description}")

        return priority_fixes


# === Performance Testing Framework ===


class PerformanceTester:
    """
    Comprehensive performance testing with Core Web Vitals

    Features:
    - Core Web Vitals measurement (LCP, FID, CLS)
    - Lighthouse-style performance scoring
    - Resource analysis and optimization suggestions
    - Network performance measurement
    - Memory usage monitoring
    - Performance budget validation
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Performance thresholds
        self.thresholds = {
            "lcp_ms": config.get("lcp_threshold", 2500),
            "fcp_ms": config.get("fcp_threshold", 1800),
            "fid_ms": config.get("fid_threshold", 100),
            "cls": config.get("cls_threshold", 0.1),
            "load_time_ms": config.get("load_time_threshold", 3000),
        }

        logger.info("Performance Tester initialized")

    async def run_comprehensive_performance_test(
        self, page: Page, context: TestContext
    ) -> PerformanceTestResult:
        """Run comprehensive performance test"""

        try:
            # Measure Core Web Vitals
            core_web_vitals = await self._measure_core_web_vitals(page)

            # Measure additional performance metrics
            additional_metrics = await self._measure_additional_metrics(page)

            # Analyze resources
            resource_analysis = await self._analyze_resources(page)

            # Generate performance insights
            opportunities, diagnostics = await self._generate_performance_insights(
                core_web_vitals, additional_metrics, resource_analysis
            )

            # Calculate overall performance score
            overall_score = self._calculate_performance_score(core_web_vitals, additional_metrics)

            result = PerformanceTestResult(
                core_web_vitals=core_web_vitals,
                overall_score=overall_score,
                opportunities=opportunities,
                diagnostics=diagnostics,
                **additional_metrics,
                **resource_analysis,
            )

            logger.info(f"Performance test completed with score: {result.get_lighthouse_score()}")
            return result

        except Exception as e:
            logger.error(f"Performance testing failed: {e}")
            return PerformanceTestResult(
                core_web_vitals=CoreWebVitals(),
                overall_score=0.0,
                opportunities=["Performance testing failed - check page performance"],
                diagnostics=[f"Error: {str(e)}"],
            )

    async def _measure_core_web_vitals(self, page: Page) -> CoreWebVitals:
        """Measure Core Web Vitals"""

        # Inject Web Vitals measurement script
        await page.add_script_tag(url="https://unpkg.com/web-vitals@latest/dist/web-vitals.umd.js")

        # Set up measurement collection
        vitals_data = await page.evaluate(
            """
            () => {
                return new Promise((resolve) => {
                    const vitals = {};
                    
                    // Measure Core Web Vitals
                    webVitals.getCLS((metric) => {
                        vitals.cls = metric.value;
                    });
                    
                    webVitals.getFCP((metric) => {
                        vitals.fcp = metric.value;
                    });
                    
                    webVitals.getFID((metric) => {
                        vitals.fid = metric.value;
                    });
                    
                    webVitals.getLCP((metric) => {
                        vitals.lcp = metric.value;
                    });
                    
                    webVitals.getTTFB((metric) => {
                        vitals.ttfb = metric.value;
                    });
                    
                    // Wait for measurements to complete
                    setTimeout(() => {
                        resolve(vitals);
                    }, 3000);
                });
            }
        """
        )

        return CoreWebVitals(
            largest_contentful_paint=vitals_data.get("lcp"),
            first_contentful_paint=vitals_data.get("fcp"),
            first_input_delay=vitals_data.get("fid"),
            cumulative_layout_shift=vitals_data.get("cls"),
        )

    async def _measure_additional_metrics(self, page: Page) -> Dict[str, Any]:
        """Measure additional performance metrics"""

        performance_data = await page.evaluate(
            """
            () => {
                const navigation = performance.getEntriesByType('navigation')[0];
                const timing = performance.timing;
                
                return {
                    load_time_ms: timing.loadEventEnd - timing.navigationStart,
                    dom_content_loaded_ms: timing.domContentLoadedEventEnd - timing.navigationStart,
                    time_to_interactive_ms: null, // Would need complex calculation
                    
                    // Memory metrics (if available)
                    js_heap_used_mb: performance.memory ? performance.memory.usedJSHeapSize / (1024 * 1024) : 0,
                    js_heap_total_mb: performance.memory ? performance.memory.totalJSHeapSize / (1024 * 1024) : 0,
                    
                    // Network metrics (if available)
                    effective_connection_type: navigator.connection ? navigator.connection.effectiveType : null,
                    bandwidth_estimate_mbps: navigator.connection ? navigator.connection.downlink : null
                };
            }
        """
        )

        return performance_data

    async def _analyze_resources(self, page: Page) -> Dict[str, Any]:
        """Analyze page resources"""

        resource_data = await page.evaluate(
            """
            () => {
                const resources = performance.getEntriesByType('resource');
                
                let totalSize = 0;
                let imageSize = 0;
                let scriptSize = 0;
                let styleSize = 0;
                let failedRequests = 0;
                
                resources.forEach(resource => {
                    const size = resource.transferSize || 0;
                    totalSize += size;
                    
                    if (resource.initiatorType === 'img') {
                        imageSize += size;
                    } else if (resource.initiatorType === 'script') {
                        scriptSize += size;
                    } else if (resource.initiatorType === 'link' && resource.name.includes('.css')) {
                        styleSize += size;
                    }
                    
                    // Check for failed requests (status >= 400)
                    if (resource.responseStatus && resource.responseStatus >= 400) {
                        failedRequests++;
                    }
                });
                
                return {
                    total_requests: resources.length,
                    failed_requests: failedRequests,
                    total_size_kb: totalSize / 1024,
                    image_size_kb: imageSize / 1024,
                    script_size_kb: scriptSize / 1024,
                    style_size_kb: styleSize / 1024
                };
            }
        """
        )

        return resource_data

    async def _generate_performance_insights(
        self,
        core_web_vitals: CoreWebVitals,
        additional_metrics: Dict[str, Any],
        resource_analysis: Dict[str, Any],
    ) -> Tuple[List[str], List[str]]:
        """Generate performance optimization opportunities and diagnostics"""

        opportunities = []
        diagnostics = []

        # Core Web Vitals opportunities
        if (
            core_web_vitals.largest_contentful_paint
            and core_web_vitals.largest_contentful_paint > self.thresholds["lcp_ms"]
        ):
            opportunities.append(
                f"Improve Largest Contentful Paint (current: {core_web_vitals.largest_contentful_paint:.0f}ms)"
            )

        if (
            core_web_vitals.first_contentful_paint
            and core_web_vitals.first_contentful_paint > self.thresholds["fcp_ms"]
        ):
            opportunities.append(
                f"Improve First Contentful Paint (current: {core_web_vitals.first_contentful_paint:.0f}ms)"
            )

        if (
            core_web_vitals.cumulative_layout_shift
            and core_web_vitals.cumulative_layout_shift > self.thresholds["cls"]
        ):
            opportunities.append(
                f"Reduce Cumulative Layout Shift (current: {core_web_vitals.cumulative_layout_shift:.3f})"
            )

        # Resource-based opportunities
        if resource_analysis["image_size_kb"] > 1000:
            opportunities.append("Optimize images - consider compression and next-gen formats")

        if resource_analysis["script_size_kb"] > 500:
            opportunities.append("Reduce JavaScript bundle size - consider code splitting")

        if resource_analysis["total_requests"] > 50:
            opportunities.append("Reduce number of HTTP requests - consider resource bundling")

        # Performance diagnostics
        if additional_metrics["load_time_ms"] > self.thresholds["load_time_ms"]:
            diagnostics.append(
                f"Page load time exceeds threshold: {additional_metrics['load_time_ms']:.0f}ms"
            )

        if resource_analysis["failed_requests"] > 0:
            diagnostics.append(
                f"{resource_analysis['failed_requests']} failed resource requests detected"
            )

        if additional_metrics["js_heap_used_mb"] > 50:
            diagnostics.append(
                f"High JavaScript memory usage: {additional_metrics['js_heap_used_mb']:.1f}MB"
            )

        # Network diagnostics
        if additional_metrics["effective_connection_type"] in ["slow-2g", "2g"]:
            diagnostics.append("Slow network connection detected - optimize for low bandwidth")

        return opportunities, diagnostics

    def _calculate_performance_score(
        self, core_web_vitals: CoreWebVitals, additional_metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall performance score (0.0 to 1.0)"""

        scores = []

        # Core Web Vitals score (60% weight)
        cwv_score = core_web_vitals.get_score()
        scores.append(cwv_score * 0.6)

        # Load time score (20% weight)
        load_time = additional_metrics.get("load_time_ms", 0)
        if load_time > 0:
            load_score = (
                1.0
                if load_time <= self.thresholds["load_time_ms"]
                else max(
                    0.0,
                    1.0
                    - (load_time - self.thresholds["load_time_ms"])
                    / self.thresholds["load_time_ms"],
                )
            )
            scores.append(load_score * 0.2)

        # Memory efficiency score (10% weight)
        js_heap = additional_metrics.get("js_heap_used_mb", 0)
        memory_score = 1.0 if js_heap <= 50 else max(0.0, 1.0 - (js_heap - 50) / 50)
        scores.append(memory_score * 0.1)

        # Resource efficiency score (10% weight)
        total_size_mb = additional_metrics.get("total_size_kb", 0) / 1024
        resource_score = 1.0 if total_size_mb <= 2 else max(0.0, 1.0 - (total_size_mb - 2) / 2)
        scores.append(resource_score * 0.1)

        return sum(scores)


# === Combined Accessibility and Performance Framework ===


class AccessibilityPerformanceFramework:
    """
    Combined accessibility and performance testing framework

    Provides comprehensive testing of both accessibility compliance
    and performance metrics in a single integrated framework.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.accessibility_tester = AccessibilityTester(config.get("accessibility", {}))
        self.performance_tester = PerformanceTester(config.get("performance", {}))

        logger.info("Accessibility & Performance Framework initialized")

    async def run_comprehensive_test(self, page: Page, context: TestContext) -> Dict[str, Any]:
        """Run comprehensive accessibility and performance testing"""

        start_time = time.time()

        try:
            # Run both tests in parallel for efficiency
            accessibility_task = self.accessibility_tester.run_comprehensive_accessibility_test(
                page, context
            )
            performance_task = self.performance_tester.run_comprehensive_performance_test(
                page, context
            )

            accessibility_result, performance_result = await asyncio.gather(
                accessibility_task, performance_task, return_exceptions=True
            )

            # Handle any exceptions
            if isinstance(accessibility_result, Exception):
                logger.error(f"Accessibility testing failed: {accessibility_result}")
                accessibility_result = AccessibilityTestResult(
                    wcag_level=WCAGLevel.AA,
                    overall_score=0.0,
                    recommendations=["Accessibility testing failed"],
                )

            if isinstance(performance_result, Exception):
                logger.error(f"Performance testing failed: {performance_result}")
                performance_result = PerformanceTestResult(
                    core_web_vitals=CoreWebVitals(),
                    overall_score=0.0,
                    opportunities=["Performance testing failed"],
                )

            # Calculate combined score
            combined_score = (
                accessibility_result.overall_score + performance_result.overall_score
            ) / 2

            # Generate combined recommendations
            combined_recommendations = self._generate_combined_recommendations(
                accessibility_result, performance_result
            )

            duration_seconds = time.time() - start_time

            result = {
                "accessibility_result": accessibility_result,
                "performance_result": performance_result,
                "combined_score": combined_score,
                "combined_recommendations": combined_recommendations,
                "test_duration_seconds": duration_seconds,
                "quality_metrics": {
                    QualityMetric.ACCESSIBILITY: accessibility_result.overall_score,
                    QualityMetric.PERFORMANCE: performance_result.overall_score,
                    QualityMetric.OVERALL: combined_score,
                },
            }

            logger.info(
                f"Combined testing completed in {duration_seconds:.2f}s with score: {combined_score:.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"Combined testing failed: {e}")
            return {
                "accessibility_result": None,
                "performance_result": None,
                "combined_score": 0.0,
                "combined_recommendations": ["Testing framework error"],
                "error": str(e),
            }

    def _generate_combined_recommendations(
        self,
        accessibility_result: AccessibilityTestResult,
        performance_result: PerformanceTestResult,
    ) -> List[str]:
        """Generate combined accessibility and performance recommendations"""

        recommendations = []

        # Priority order: Critical accessibility issues first
        if accessibility_result.priority_fixes:
            recommendations.extend(accessibility_result.priority_fixes)

        # High-impact performance issues
        critical_performance = [
            opp
            for opp in performance_result.opportunities
            if "Largest Contentful Paint" in opp or "Cumulative Layout Shift" in opp
        ]
        recommendations.extend(critical_performance)

        # General accessibility recommendations
        accessibility_recommendations = [
            rec
            for rec in accessibility_result.recommendations
            if not any(priority in rec for priority in ["CRITICAL", "SERIOUS"])
        ]
        recommendations.extend(accessibility_recommendations[:3])  # Limit to top 3

        # General performance recommendations
        performance_recommendations = [
            opp for opp in performance_result.opportunities if opp not in critical_performance
        ]
        recommendations.extend(performance_recommendations[:3])  # Limit to top 3

        # Combined insights
        if accessibility_result.overall_score > 0.9 and performance_result.overall_score > 0.9:
            recommendations.append(
                "Excellent accessibility and performance - maintain current standards!"
            )
        elif accessibility_result.overall_score < 0.7 or performance_result.overall_score < 0.7:
            recommendations.append(
                "Both accessibility and performance need attention for optimal user experience"
            )

        return recommendations


# === Export Framework Components ===

__all__ = [
    "AccessibilityTester",
    "PerformanceTester",
    "AccessibilityPerformanceFramework",
    "AccessibilityTestResult",
    "PerformanceTestResult",
    "CoreWebVitals",
    "WCAGLevel",
]
