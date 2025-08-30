"""
UI Testing Framework with Visual Regression

Advanced UI testing framework for Novel-Engine with visual regression testing,
responsive design validation, and user interaction simulation.
"""

import asyncio
import hashlib
import logging
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Import AI testing contracts
from ai_testing.interfaces.service_contracts import (
    TestContext,
    UITestSpec,
)

# Import Novel-Engine patterns
from PIL import Image, ImageChops
from playwright.async_api import Page

from src.event_bus import EventBus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Visual Testing Models ===

class VisualDiff:
    """Visual difference detection and analysis"""
    
    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold
    
    def compare_images(
        self,
        image1_path: str,
        image2_path: str,
        output_diff_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compare two images and return difference metrics"""
        
        try:
            # Load images
            img1 = Image.open(image1_path).convert('RGB')
            img2 = Image.open(image2_path).convert('RGB')
            
            # Ensure same size
            if img1.size != img2.size:
                # Resize to larger dimensions
                max_width = max(img1.width, img2.width)
                max_height = max(img1.height, img2.height)
                
                img1 = img1.resize((max_width, max_height), Image.Resampling.LANCZOS)
                img2 = img2.resize((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Calculate pixel difference
            diff_img = ImageChops.difference(img1, img2)
            
            # Convert to numpy arrays for analysis
            img1_array = np.array(img1)
            np.array(img2)
            diff_array = np.array(diff_img)
            
            # Calculate metrics
            total_pixels = img1_array.shape[0] * img1_array.shape[1]
            diff_pixels = np.sum(np.any(diff_array > 0, axis=2))
            diff_percentage = (diff_pixels / total_pixels) * 100
            
            # Calculate average color difference
            avg_diff = np.mean(diff_array)
            max_diff = np.max(diff_array)
            
            # Save diff image if requested
            if output_diff_path:
                diff_img.save(output_diff_path)
            
            # Determine if images match
            images_match = diff_percentage <= self.threshold
            
            return {
                "images_match": images_match,
                "diff_percentage": diff_percentage,
                "avg_color_diff": float(avg_diff),
                "max_color_diff": float(max_diff),
                "total_pixels": total_pixels,
                "different_pixels": int(diff_pixels),
                "threshold": self.threshold,
                "diff_image_path": output_diff_path
            }
            
        except Exception as e:
            logger.error(f"Image comparison failed: {e}")
            return {
                "images_match": False,
                "diff_percentage": 100.0,
                "error": str(e)
            }

class ResponsiveTestSuite:
    """Responsive design testing across multiple viewports"""
    
    VIEWPORT_PRESETS = {
        "mobile_portrait": {"width": 375, "height": 667},      # iPhone SE
        "mobile_landscape": {"width": 667, "height": 375},     # iPhone SE landscape
        "tablet_portrait": {"width": 768, "height": 1024},     # iPad
        "tablet_landscape": {"width": 1024, "height": 768},    # iPad landscape
        "desktop_small": {"width": 1280, "height": 720},       # HD
        "desktop_medium": {"width": 1440, "height": 900},      # MacBook Air
        "desktop_large": {"width": 1920, "height": 1080},      # Full HD
        "desktop_xl": {"width": 2560, "height": 1440}          # 2K
    }
    
    def __init__(self):
        self.visual_diff = VisualDiff(threshold=0.05)  # Stricter for responsive testing
    
    async def test_responsive_design(
        self,
        page: Page,
        page_url: str,
        viewports: List[str] = None,
        capture_screenshots: bool = True
    ) -> Dict[str, Any]:
        """Test responsive design across multiple viewports"""
        
        viewports = viewports or ["mobile_portrait", "tablet_portrait", "desktop_medium"]
        results = {
            "viewport_tests": {},
            "responsive_score": 0.0,
            "layout_issues": [],
            "screenshots": {},
            "recommendations": []
        }
        
        screenshots = {}
        layout_scores = []
        
        for viewport_name in viewports:
            if viewport_name not in self.VIEWPORT_PRESETS:
                logger.warning(f"Unknown viewport preset: {viewport_name}")
                continue
            
            viewport = self.VIEWPORT_PRESETS[viewport_name]
            
            try:
                # Set viewport
                await page.set_viewport_size(viewport["width"], viewport["height"])
                await page.goto(page_url)
                await page.wait_for_load_state('networkidle')
                
                # Test responsive layout
                layout_result = await self._test_viewport_layout(page, viewport_name)
                results["viewport_tests"][viewport_name] = layout_result
                layout_scores.append(layout_result["layout_score"])
                
                # Capture screenshot
                if capture_screenshots:
                    screenshot_path = f"responsive_{viewport_name}_{int(time.time())}.png"
                    await page.screenshot(path=screenshot_path, full_page=True)
                    screenshots[viewport_name] = screenshot_path
                
                logger.info(f"Responsive test completed for {viewport_name}")
                
            except Exception as e:
                logger.error(f"Responsive test failed for {viewport_name}: {e}")
                results["viewport_tests"][viewport_name] = {
                    "layout_score": 0.0,
                    "error": str(e)
                }
                layout_scores.append(0.0)
        
        # Calculate overall responsive score
        results["responsive_score"] = statistics.mean(layout_scores) if layout_scores else 0.0
        results["screenshots"] = screenshots
        
        # Generate recommendations
        results["recommendations"] = self._generate_responsive_recommendations(results)
        
        return results
    
    async def _test_viewport_layout(
        self,
        page: Page,
        viewport_name: str
    ) -> Dict[str, Any]:
        """Test layout quality for specific viewport"""
        
        layout_checks = await page.evaluate("""
            () => {
                const results = {
                    horizontal_scroll: document.documentElement.scrollWidth > window.innerWidth,
                    viewport_meta_tag: !!document.querySelector('meta[name="viewport"]'),
                    responsive_images: 0,
                    fixed_width_elements: 0,
                    overflow_elements: 0,
                    touch_targets: 0,
                    readable_text: true
                };
                
                // Check images
                const images = document.querySelectorAll('img');
                images.forEach(img => {
                    const style = window.getComputedStyle(img);
                    if (style.maxWidth === '100%' || style.width === '100%') {
                        results.responsive_images++;
                    }
                });
                
                // Check for fixed width elements
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    
                    // Check for fixed widths
                    if (style.width && style.width.includes('px') && 
                        parseInt(style.width) > window.innerWidth) {
                        results.fixed_width_elements++;
                    }
                    
                    // Check for overflow
                    if (style.overflow === 'hidden' && el.scrollWidth > el.clientWidth) {
                        results.overflow_elements++;
                    }
                });
                
                // Check touch targets (buttons, links)
                const touchTargets = document.querySelectorAll('button, a, input[type="submit"]');
                touchTargets.forEach(target => {
                    const rect = target.getBoundingClientRect();
                    if (rect.width >= 44 && rect.height >= 44) {
                        results.touch_targets++;
                    }
                });
                
                // Check text readability
                const textElements = document.querySelectorAll('p, span, div, h1, h2, h3, h4, h5, h6');
                let readableTextCount = 0;
                textElements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    const fontSize = parseInt(style.fontSize);
                    if (fontSize >= 16) {
                        readableTextCount++;
                    }
                });
                
                results.readable_text = readableTextCount / Math.max(textElements.length, 1) > 0.8;
                results.total_images = images.length;
                results.total_touch_targets = touchTargets.length;
                
                return results;
            }
        """)
        
        # Calculate layout score
        score_factors = []
        
        # No horizontal scroll (critical)
        score_factors.append(0.0 if layout_checks["horizontal_scroll"] else 1.0)
        
        # Viewport meta tag present
        score_factors.append(1.0 if layout_checks["viewport_meta_tag"] else 0.5)
        
        # Responsive images ratio
        if layout_checks["total_images"] > 0:
            responsive_ratio = layout_checks["responsive_images"] / layout_checks["total_images"]
            score_factors.append(responsive_ratio)
        else:
            score_factors.append(1.0)
        
        # Touch target adequacy (for mobile)
        if viewport_name.startswith("mobile") and layout_checks["total_touch_targets"] > 0:
            touch_ratio = layout_checks["touch_targets"] / layout_checks["total_touch_targets"]
            score_factors.append(touch_ratio)
        else:
            score_factors.append(1.0)
        
        # Readable text
        score_factors.append(1.0 if layout_checks["readable_text"] else 0.7)
        
        # Fixed width elements penalty
        fixed_width_penalty = min(layout_checks["fixed_width_elements"] * 0.1, 0.5)
        score_factors.append(1.0 - fixed_width_penalty)
        
        layout_score = statistics.mean(score_factors)
        
        return {
            "layout_score": layout_score,
            "layout_checks": layout_checks,
            "score_factors": score_factors,
            "issues": self._identify_layout_issues(layout_checks, viewport_name)
        }
    
    def _identify_layout_issues(
        self,
        layout_checks: Dict[str, Any],
        viewport_name: str
    ) -> List[str]:
        """Identify specific layout issues"""
        issues = []
        
        if layout_checks["horizontal_scroll"]:
            issues.append("Horizontal scrollbar present - content too wide")
        
        if not layout_checks["viewport_meta_tag"]:
            issues.append("Missing viewport meta tag")
        
        if layout_checks["total_images"] > 0:
            responsive_ratio = layout_checks["responsive_images"] / layout_checks["total_images"]
            if responsive_ratio < 0.8:
                issues.append(f"Only {responsive_ratio:.1%} of images are responsive")
        
        if layout_checks["fixed_width_elements"] > 0:
            issues.append(f"{layout_checks['fixed_width_elements']} elements have fixed widths")
        
        if viewport_name.startswith("mobile"):
            if layout_checks["total_touch_targets"] > 0:
                touch_ratio = layout_checks["touch_targets"] / layout_checks["total_touch_targets"]
                if touch_ratio < 0.8:
                    issues.append(f"Only {touch_ratio:.1%} of touch targets meet minimum size (44px)")
        
        if not layout_checks["readable_text"]:
            issues.append("Text may be too small for comfortable reading")
        
        return issues
    
    def _generate_responsive_recommendations(
        self,
        results: Dict[str, Any]
    ) -> List[str]:
        """Generate responsive design recommendations"""
        recommendations = []
        
        # Overall score recommendations
        if results["responsive_score"] < 0.7:
            recommendations.append("Responsive design needs significant improvement")
        elif results["responsive_score"] < 0.9:
            recommendations.append("Responsive design is good but has room for improvement")
        else:
            recommendations.append("Excellent responsive design implementation")
        
        # Specific viewport recommendations
        for viewport_name, viewport_result in results["viewport_tests"].items():
            if "error" in viewport_result:
                recommendations.append(f"{viewport_name}: Test failed - {viewport_result['error']}")
                continue
            
            score = viewport_result["layout_score"]
            if score < 0.7:
                recommendations.append(f"{viewport_name}: Layout issues detected (score: {score:.2f})")
            
            # Add specific issues
            for issue in viewport_result.get("issues", []):
                recommendations.append(f"{viewport_name}: {issue}")
        
        return recommendations

class InteractionTestSuite:
    """User interaction testing and validation"""
    
    def __init__(self):
        self.interaction_timeout_ms = 5000
    
    async def test_form_interactions(
        self,
        page: Page,
        form_selector: str = "form"
    ) -> Dict[str, Any]:
        """Test form interaction patterns"""
        
        results = {
            "forms_found": 0,
            "input_tests": {},
            "validation_tests": {},
            "submission_tests": {},
            "accessibility_score": 0.0,
            "usability_score": 0.0,
            "recommendations": []
        }
        
        # Find forms
        forms = await page.locator(form_selector).all()
        results["forms_found"] = len(forms)
        
        if not forms:
            results["recommendations"].append("No forms found to test")
            return results
        
        for i, form in enumerate(forms):
            form_id = f"form_{i}"
            
            # Test input fields
            input_result = await self._test_form_inputs(page, form, form_id)
            results["input_tests"][form_id] = input_result
            
            # Test form validation
            validation_result = await self._test_form_validation(page, form, form_id)
            results["validation_tests"][form_id] = validation_result
            
            # Test form submission
            submission_result = await self._test_form_submission(page, form, form_id)
            results["submission_tests"][form_id] = submission_result
        
        # Calculate scores
        results["accessibility_score"] = self._calculate_form_accessibility_score(results)
        results["usability_score"] = self._calculate_form_usability_score(results)
        
        # Generate recommendations
        results["recommendations"] = self._generate_form_recommendations(results)
        
        return results
    
    async def _test_form_inputs(
        self,
        page: Page,
        form,
        form_id: str
    ) -> Dict[str, Any]:
        """Test form input interactions"""
        
        input_result = {
            "inputs_found": 0,
            "inputs_accessible": 0,
            "inputs_with_labels": 0,
            "inputs_with_placeholders": 0,
            "input_types": {},
            "keyboard_navigation": True
        }
        
        # Find all inputs
        inputs = await form.locator("input, textarea, select").all()
        input_result["inputs_found"] = len(inputs)
        
        for input_element in inputs:
            try:
                # Check accessibility
                input_type = await input_element.get_attribute("type") or "text"
                input_result["input_types"][input_type] = input_result["input_types"].get(input_type, 0) + 1
                
                # Check if input is accessible
                if await input_element.is_visible() and await input_element.is_enabled():
                    input_result["inputs_accessible"] += 1
                
                # Check for label
                input_id = await input_element.get_attribute("id")
                if input_id:
                    label = await page.locator(f"label[for='{input_id}']").count()
                    if label > 0:
                        input_result["inputs_with_labels"] += 1
                
                # Check for placeholder
                placeholder = await input_element.get_attribute("placeholder")
                if placeholder:
                    input_result["inputs_with_placeholders"] += 1
                
                # Test keyboard navigation
                try:
                    await input_element.focus()
                    await page.keyboard.press("Tab")
                except Exception:
                    input_result["keyboard_navigation"] = False
                
            except Exception as e:
                logger.warning(f"Input testing failed: {e}")
        
        return input_result
    
    async def _test_form_validation(
        self,
        page: Page,
        form,
        form_id: str
    ) -> Dict[str, Any]:
        """Test form validation behavior"""
        
        validation_result = {
            "required_fields": 0,
            "validation_messages": 0,
            "client_side_validation": False,
            "validation_timing": "unknown"
        }
        
        # Find required fields
        required_inputs = await form.locator("input[required], textarea[required], select[required]").all()
        validation_result["required_fields"] = len(required_inputs)
        
        if required_inputs:
            try:
                # Test validation by submitting empty form
                submit_button = form.locator("input[type='submit'], button[type='submit']").first
                
                if await submit_button.count() > 0:
                    await submit_button.click()
                    
                    # Wait a moment for validation messages
                    await asyncio.sleep(0.5)
                    
                    # Check for validation messages
                    validation_messages = await page.locator(".error, .invalid, [aria-invalid='true']").count()
                    validation_result["validation_messages"] = validation_messages
                    validation_result["client_side_validation"] = validation_messages > 0
                
            except Exception as e:
                logger.warning(f"Form validation testing failed: {e}")
        
        return validation_result
    
    async def _test_form_submission(
        self,
        page: Page,
        form,
        form_id: str
    ) -> Dict[str, Any]:
        """Test form submission behavior"""
        
        submission_result = {
            "submit_buttons": 0,
            "submission_method": "unknown",
            "prevents_double_submission": False,
            "shows_loading_state": False
        }
        
        # Find submit buttons
        submit_buttons = await form.locator("input[type='submit'], button[type='submit']").all()
        submission_result["submit_buttons"] = len(submit_buttons)
        
        # Check form method
        method = await form.get_attribute("method")
        submission_result["submission_method"] = method or "get"
        
        # Test submission behavior (would need more complex setup for actual testing)
        
        return submission_result
    
    def _calculate_form_accessibility_score(self, results: Dict[str, Any]) -> float:
        """Calculate form accessibility score"""
        scores = []
        
        for form_result in results["input_tests"].values():
            if form_result["inputs_found"] > 0:
                label_ratio = form_result["inputs_with_labels"] / form_result["inputs_found"]
                accessible_ratio = form_result["inputs_accessible"] / form_result["inputs_found"]
                keyboard_score = 1.0 if form_result["keyboard_navigation"] else 0.0
                
                form_score = (label_ratio + accessible_ratio + keyboard_score) / 3
                scores.append(form_score)
        
        return statistics.mean(scores) if scores else 1.0
    
    def _calculate_form_usability_score(self, results: Dict[str, Any]) -> float:
        """Calculate form usability score"""
        scores = []
        
        for form_id in results["input_tests"].keys():
            input_result = results["input_tests"][form_id]
            validation_result = results["validation_tests"][form_id]
            
            # Usability factors
            placeholder_ratio = 0.0
            if input_result["inputs_found"] > 0:
                placeholder_ratio = input_result["inputs_with_placeholders"] / input_result["inputs_found"]
            
            validation_score = 1.0 if validation_result["client_side_validation"] else 0.5
            
            form_usability = (placeholder_ratio + validation_score) / 2
            scores.append(form_usability)
        
        return statistics.mean(scores) if scores else 1.0
    
    def _generate_form_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate form testing recommendations"""
        recommendations = []
        
        if results["forms_found"] == 0:
            return ["No forms found to test"]
        
        # Accessibility recommendations
        if results["accessibility_score"] < 0.8:
            recommendations.append("Form accessibility needs improvement")
            
            for form_id, input_result in results["input_tests"].items():
                if input_result["inputs_found"] > 0:
                    label_ratio = input_result["inputs_with_labels"] / input_result["inputs_found"]
                    if label_ratio < 0.9:
                        recommendations.append(f"{form_id}: Add labels to all form inputs")
                    
                    if not input_result["keyboard_navigation"]:
                        recommendations.append(f"{form_id}: Improve keyboard navigation support")
        
        # Usability recommendations
        if results["usability_score"] < 0.8:
            recommendations.append("Form usability could be enhanced")
            
            for form_id, validation_result in results["validation_tests"].items():
                if not validation_result["client_side_validation"]:
                    recommendations.append(f"{form_id}: Add client-side validation for better UX")
        
        return recommendations

# === Main UI Testing Framework ===

class UITestingFramework:
    """
    Comprehensive UI testing framework for Novel-Engine
    
    Features:
    - Visual regression testing
    - Responsive design validation
    - User interaction testing
    - Accessibility compliance
    - Performance measurement
    - Cross-browser compatibility
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.event_bus = EventBus()
        
        # Initialize testing suites
        self.visual_diff = VisualDiff(threshold=config.get("visual_threshold", 0.1))
        self.responsive_suite = ResponsiveTestSuite()
        self.interaction_suite = InteractionTestSuite()
        
        # Configuration
        self.screenshots_dir = Path(config.get("screenshots_dir", "ai_testing/screenshots"))
        self.baseline_dir = Path(config.get("baseline_dir", "ai_testing/baselines"))
        
        # Ensure directories exist
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("UI Testing Framework initialized")
    
    async def run_comprehensive_ui_test(
        self,
        page: Page,
        test_spec: UITestSpec,
        context: TestContext
    ) -> Dict[str, Any]:
        """Run comprehensive UI test suite"""
        
        results = {
            "basic_ui_test": {},
            "visual_regression": {},
            "responsive_design": {},
            "interaction_testing": {},
            "overall_score": 0.0,
            "recommendations": []
        }
        
        start_time = time.time()
        
        try:
            # Navigate to page
            await page.goto(test_spec.page_url)
            await page.wait_for_load_state('networkidle')
            
            # Basic UI test
            if test_spec.actions or test_spec.assertions:
                results["basic_ui_test"] = await self._run_basic_ui_test(page, test_spec)
            
            # Visual regression testing
            if test_spec.screenshot_comparison:
                results["visual_regression"] = await self._run_visual_regression_test(
                    page, test_spec.page_url, test_spec.visual_threshold
                )
            
            # Responsive design testing
            results["responsive_design"] = await self.responsive_suite.test_responsive_design(
                page, test_spec.page_url
            )
            
            # Interaction testing
            results["interaction_testing"] = await self.interaction_suite.test_form_interactions(page)
            
            # Calculate overall score
            results["overall_score"] = self._calculate_overall_ui_score(results)
            
            # Generate comprehensive recommendations
            results["recommendations"] = self._generate_comprehensive_recommendations(results)
            
            logger.info(f"Comprehensive UI test completed in {time.time() - start_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Comprehensive UI test failed: {e}")
            results["error"] = str(e)
            results["overall_score"] = 0.0
        
        return results
    
    async def _run_basic_ui_test(
        self,
        page: Page,
        test_spec: UITestSpec
    ) -> Dict[str, Any]:
        """Run basic UI actions and assertions"""
        
        results = {
            "actions_completed": 0,
            "assertions_passed": 0,
            "total_actions": len(test_spec.actions),
            "total_assertions": len(test_spec.assertions),
            "errors": []
        }
        
        # Execute actions
        for i, action in enumerate(test_spec.actions):
            try:
                await self._execute_action(page, action)
                results["actions_completed"] += 1
            except Exception as e:
                results["errors"].append(f"Action {i}: {str(e)}")
        
        # Execute assertions
        for i, assertion in enumerate(test_spec.assertions):
            try:
                assertion_passed = await self._execute_assertion(page, assertion)
                if assertion_passed:
                    results["assertions_passed"] += 1
            except Exception as e:
                results["errors"].append(f"Assertion {i}: {str(e)}")
        
        # Calculate success rates
        results["action_success_rate"] = results["actions_completed"] / max(results["total_actions"], 1)
        results["assertion_success_rate"] = results["assertions_passed"] / max(results["total_assertions"], 1)
        
        return results
    
    async def _run_visual_regression_test(
        self,
        page: Page,
        page_url: str,
        threshold: float
    ) -> Dict[str, Any]:
        """Run visual regression testing"""
        
        # Generate screenshot filename
        url_hash = hashlib.md5(page_url.encode()).hexdigest()[:8]
        screenshot_name = f"visual_test_{url_hash}"
        
        # Capture current screenshot
        current_screenshot = self.screenshots_dir / f"{screenshot_name}_current.png"
        await page.screenshot(path=str(current_screenshot), full_page=True)
        
        # Check for baseline
        baseline_screenshot = self.baseline_dir / f"{screenshot_name}_baseline.png"
        
        if not baseline_screenshot.exists():
            # Create baseline
            baseline_screenshot.parent.mkdir(parents=True, exist_ok=True)
            current_screenshot.rename(baseline_screenshot)
            
            return {
                "baseline_created": True,
                "visual_match": True,
                "diff_percentage": 0.0,
                "baseline_path": str(baseline_screenshot)
            }
        
        # Compare with baseline
        diff_path = self.screenshots_dir / f"{screenshot_name}_diff.png"
        comparison_result = self.visual_diff.compare_images(
            str(baseline_screenshot),
            str(current_screenshot),
            str(diff_path)
        )
        
        return {
            "baseline_created": False,
            "visual_match": comparison_result["images_match"],
            "diff_percentage": comparison_result["diff_percentage"],
            "baseline_path": str(baseline_screenshot),
            "current_path": str(current_screenshot),
            "diff_path": str(diff_path) if comparison_result["images_match"] else None,
            "comparison_details": comparison_result
        }
    
    async def _execute_action(self, page: Page, action: Dict[str, Any]):
        """Execute UI action"""
        action_type = action["type"]
        selector = action["selector"]
        value = action.get("value", "")
        
        if action_type == "click":
            await page.click(selector)
        elif action_type == "type":
            await page.fill(selector, value)
        elif action_type == "select":
            await page.select_option(selector, value)
        elif action_type == "hover":
            await page.hover(selector)
        elif action_type == "wait":
            await asyncio.sleep(float(value))
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    async def _execute_assertion(self, page: Page, assertion: Dict[str, Any]) -> bool:
        """Execute UI assertion"""
        assertion_type = assertion["type"]
        selector = assertion.get("selector")
        expected = assertion.get("expected", "")
        
        if assertion_type == "visible":
            return await page.is_visible(selector)
        elif assertion_type == "text":
            element_text = await page.inner_text(selector)
            return expected in element_text
        elif assertion_type == "value":
            element_value = await page.input_value(selector)
            return element_value == expected
        elif assertion_type == "count":
            count = await page.locator(selector).count()
            return count == int(expected)
        elif assertion_type == "url":
            return expected in page.url
        else:
            raise ValueError(f"Unknown assertion type: {assertion_type}")
    
    def _calculate_overall_ui_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall UI test score"""
        scores = []
        
        # Basic UI test score
        if results.get("basic_ui_test"):
            basic_result = results["basic_ui_test"]
            action_score = basic_result.get("action_success_rate", 0.0)
            assertion_score = basic_result.get("assertion_success_rate", 0.0)
            basic_score = (action_score + assertion_score) / 2
            scores.append(basic_score)
        
        # Visual regression score
        if results.get("visual_regression"):
            visual_result = results["visual_regression"]
            visual_score = 1.0 if visual_result.get("visual_match", False) else 0.5
            scores.append(visual_score)
        
        # Responsive design score
        if results.get("responsive_design"):
            responsive_score = results["responsive_design"].get("responsive_score", 0.0)
            scores.append(responsive_score)
        
        # Interaction testing score
        if results.get("interaction_testing"):
            interaction_result = results["interaction_testing"]
            accessibility_score = interaction_result.get("accessibility_score", 1.0)
            usability_score = interaction_result.get("usability_score", 1.0)
            interaction_score = (accessibility_score + usability_score) / 2
            scores.append(interaction_score)
        
        return statistics.mean(scores) if scores else 0.0
    
    def _generate_comprehensive_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate comprehensive UI testing recommendations"""
        recommendations = []
        
        # Basic UI recommendations
        if results.get("basic_ui_test"):
            basic_result = results["basic_ui_test"]
            if basic_result.get("action_success_rate", 1.0) < 0.9:
                recommendations.append("Some UI actions failed - check selectors and timing")
            if basic_result.get("assertion_success_rate", 1.0) < 0.9:
                recommendations.append("Some UI assertions failed - verify expected states")
        
        # Visual regression recommendations
        if results.get("visual_regression"):
            visual_result = results["visual_regression"]
            if not visual_result.get("visual_match", True):
                diff_percentage = visual_result.get("diff_percentage", 0.0)
                recommendations.append(f"Visual differences detected ({diff_percentage:.1f}% different)")
        
        # Responsive design recommendations
        if results.get("responsive_design"):
            responsive_result = results["responsive_design"]
            recommendations.extend(responsive_result.get("recommendations", []))
        
        # Interaction testing recommendations
        if results.get("interaction_testing"):
            interaction_result = results["interaction_testing"]
            recommendations.extend(interaction_result.get("recommendations", []))
        
        # Overall recommendations
        overall_score = results.get("overall_score", 0.0)
        if overall_score < 0.7:
            recommendations.append("UI testing reveals significant issues requiring attention")
        elif overall_score < 0.9:
            recommendations.append("UI testing shows good results with room for improvement")
        else:
            recommendations.append("Excellent UI implementation - all tests passed successfully")
        
        return recommendations

# === Export Framework Components ===

__all__ = [
    "UITestingFramework",
    "VisualDiff",
    "ResponsiveTestSuite",
    "InteractionTestSuite"
]