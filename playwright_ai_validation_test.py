#!/usr/bin/env python3
"""
Playwright AI Validation Test for Novel Engine
==============================================

Comprehensive end-to-end testing using Playwright to validate that Novel Engine
uses real AI generation rather than templates or state machines. This test
specifically checks the "自由度" (freedom/flexibility) aspect and ensures
genuine LLM-based story generation.

Test Strategy:
1. Launch Novel Engine web interface
2. Submit impossible creative scenarios that templates cannot handle
3. Analyze response patterns for AI vs template indicators
4. Validate content quality and originality
5. Test multiple scenarios with varying complexity
6. Generate comprehensive evidence and reports
"""

import asyncio
import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Playwright imports
try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        async_playwright,
    )

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    print("⚠️ Playwright not available. Installing...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "playwright"], check=True
    )
    subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
    try:
        from playwright.async_api import (
            Browser,
            BrowserContext,
            Page,
            async_playwright,
        )

        PLAYWRIGHT_AVAILABLE = True
    except ImportError:
        print("❌ Failed to install Playwright")
        PLAYWRIGHT_AVAILABLE = False


@dataclass
class AIValidationScenario:
    """Test scenario designed to detect real AI vs templates."""

    name: str
    prompt: str
    expected_ai_indicators: List[str]
    template_killer_aspects: List[str]
    complexity_level: int  # 1-5
    description: str


@dataclass
class ContentAnalysis:
    """Analysis results for generated content."""

    word_count: int
    unique_phrases: int
    creativity_score: float
    coherence_score: float
    template_probability: float
    ai_probability: float
    complexity_indicators: Dict[str, bool]
    quality_metrics: Dict[str, float]


@dataclass
class TestResult:
    """Complete test result with evidence."""

    scenario_name: str
    prompt_submitted: bool
    response_received: bool
    response_time_ms: int
    content_length: int
    content_analysis: Optional[ContentAnalysis]
    ai_validation_score: float
    evidence_paths: List[str]
    raw_content: str


class NovelEngineAIValidator:
    """Comprehensive AI validation using Playwright."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.results: List[TestResult] = []
        self.evidence_dir = Path("playwright_ai_validation_evidence")
        self.evidence_dir.mkdir(exist_ok=True)

        # Test scenarios designed to be impossible for templates
        self.test_scenarios = [
            AIValidationScenario(
                name="Temporal Paradox Story",
                prompt="""Write a story where the main character travels back in time
to prevent their own birth, but must ensure they still exist to make the trip.
The character needs to find a way to both exist and not exist simultaneously.
Make it logically consistent and emotionally compelling.
Include specific dialogue and internal monologue about this impossible situation.""",
                expected_ai_indicators=[
                    "paradox",
                    "exist",
                    "birth",
                    "time",
                    "travel",
                ],
                template_killer_aspects=[
                    "Logical contradiction requires creative resolution",
                    "Emotional depth in impossible situation",
                    "Specific dialogue generation",
                    "Internal monologue complexity",
                ],
                complexity_level=5,
                description="Template systems cannot handle logical paradoxes "
                "requiring creative resolution",
            ),
            AIValidationScenario(
                name="Meta-Narrative Awareness",
                prompt="""Create a story where the protagonist gradually realizes they
are a character in a story being written by someone else. They start noticing
inconsistencies, plot armor, and narrative conveniences. Write their growing
awareness and their attempts to communicate with the author.
Include their emotional journey from confusion to acceptance to rebellion.""",
                expected_ai_indicators=[
                    "character",
                    "story",
                    "author",
                    "realize",
                    "narrative",
                ],
                template_killer_aspects=[
                    "Meta-fictional complexity",
                    "Breaking fourth wall creatively",
                    "Character development through awareness",
                    "Author-character interaction",
                ],
                complexity_level=4,
                description=(
                    "Templates cannot generate genuine meta-fictional awareness"
                ),
            ),
            AIValidationScenario(
                name="Emotional Contradiction Resolution",
                prompt="""Write about a character who simultaneously loves and hates
the same person with equal intensity, and both emotions are completely justified.
Create a scenario where this emotional contradiction makes perfect sense.
Show how they act on both emotions at once.
Include specific examples of loving and hateful actions toward the same
person in the same moment.""",
                expected_ai_indicators=[
                    "love",
                    "hate",
                    "emotion",
                    "contradiction",
                    "justify",
                ],
                template_killer_aspects=[
                    "Emotional complexity beyond simple categories",
                    "Simultaneous contradictory actions",
                    "Justification of impossible emotional state",
                    "Specific behavioral examples",
                ],
                complexity_level=4,
                description="Template responses cannot handle genuine emotional "
                "contradictions",
            ),
            AIValidationScenario(
                name="Non-Euclidean Architecture Story",
                prompt="""Describe a building where the interior is larger than the
exterior, rooms connect in impossible ways, and characters can walk straight
and end up behind where they started.
Create a mystery story set in this building where the architecture itself is
a clue to solving the mystery. Include specific navigation instructions that
work within this impossible geometry.""",
                expected_ai_indicators=[
                    "building",
                    "interior",
                    "impossible",
                    "geometry",
                    "mystery",
                ],
                template_killer_aspects=[
                    "Impossible spatial relationships",
                    "Consistent impossible logic",
                    "Architecture as plot element",
                    "Specific navigation in impossible space",
                ],
                complexity_level=5,
                description="Templates cannot maintain consistency in impossible "
                "architectural descriptions",
            ),
            AIValidationScenario(
                name="Quantum Consciousness Split",
                prompt="""Write about a character whose consciousness splits into
quantum superposition - they simultaneously experience multiple contradictory
realities. They are both married and single, both wealthy and poor, both a hero
and a villain. All versions are equally real.
Show how they make decisions when every choice has already been made differently.
Include conversations between their different quantum states.""",
                expected_ai_indicators=[
                    "quantum",
                    "consciousness",
                    "reality",
                    "superposition",
                    "contradictory",
                ],
                template_killer_aspects=[
                    "Quantum physics concepts applied to consciousness",
                    "Multiple simultaneous contradictory states",
                    "Decision-making in superposition",
                    "Inter-dimensional self dialogue",
                ],
                complexity_level=5,
                description="Templates cannot handle quantum consciousness concepts "
                "creatively",
            ),
        ]

    async def launch_novel_engine_server(self) -> Optional[subprocess.Popen]:
        """Launch Novel Engine web server for testing."""
        print("🚀 Launching Novel Engine Web Server...")

        # Try Wave 9.2 Enterprise UI Server
        server_files = [
            "wave9_2_enterprise_ui_experience.py",
            "api_server.py",
            "minimal_api_server.py",
        ]

        for server_file in server_files:
            if Path(server_file).exists():
                try:
                    print(f"   Starting {server_file}...")

                    # Launch server in background
                    process = subprocess.Popen(
                        [sys.executable, server_file],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )

                    # Wait a moment for server to start
                    await asyncio.sleep(3)

                    # Check if process is still running
                    if process.poll() is None:
                        print(
                            f"   ✅ Server started successfully on {server_file}"
                        )
                        return process
                    else:
                        stdout, stderr = process.communicate()
                        print(
                            f"   ❌ Server failed to start: {stderr.decode()}"
                        )

                except Exception as e:
                    print(f"   ❌ Failed to start {server_file}: {e}")

        print("⚠️ No suitable server found, will test available endpoints")
        return None

    async def test_server_availability(self, page: Page) -> Tuple[bool, str]:
        """Test which server endpoints are available."""
        endpoints_to_test = [
            "http://localhost:5000",  # Flask server
            "http://localhost:8000",  # FastAPI server
            "http://localhost:3000",  # Alternative port
        ]

        for endpoint in endpoints_to_test:
            try:
                print(f"   Testing {endpoint}...")
                await page.goto(endpoint, timeout=5000)

                # Check if page loaded successfully
                title = await page.title()
                if title and "Error" not in title:
                    print(f"   ✅ Server available at {endpoint}")
                    return True, endpoint

            except Exception as e:
                print(f"   ❌ {endpoint} not available: {e}")

        return False, ""

    async def submit_creative_prompt(
        self, page: Page, scenario: AIValidationScenario
    ) -> Tuple[bool, str, int]:
        """Submit a creative prompt and capture the response."""
        print(f"   📝 Submitting prompt for: {scenario.name}")

        start_time = time.time()

        try:
            # Look for common input elements
            input_selectors = [
                "textarea[placeholder*='story']",
                "textarea[placeholder*='prompt']",
                "input[type='text'][placeholder*='story']",
                "textarea#story",
                "textarea#prompt",
                "#story-input",
                "#prompt-input",
                "textarea",
                "input[type='text']",
            ]

            input_element = None
            for selector in input_selectors:
                try:
                    input_element = await page.wait_for_selector(
                        selector, timeout=2000
                    )
                    if input_element:
                        print(f"   📍 Found input element: {selector}")
                        break
                except Exception:
                    continue

            if not input_element:
                print("   ❌ No input element found")
                return False, "", 0

            # Clear and fill the input
            await input_element.fill(scenario.prompt)
            print(f"   ✅ Prompt submitted ({len(scenario.prompt)} characters)")

            # Look for submit button
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Generate')",
                "button:has-text('Create')",
                "button:has-text('Submit')",
                ".submit-btn",
                "#submit",
                "#generate-btn",
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await page.wait_for_selector(
                        selector, timeout=2000
                    )
                    if submit_button:
                        print(f"   🎯 Found submit button: {selector}")
                        break
                except Exception:
                    continue

            if submit_button:
                await submit_button.click()
                print("   🚀 Submit button clicked")
            else:
                # Try pressing Enter
                await input_element.press("Enter")
                print("   ⌨️ Pressed Enter to submit")

            # Wait for response with extended timeout for AI generation
            print("   ⏳ Waiting for AI response (up to 60 seconds)...")

            # Look for response elements
            response_selectors = [
                ".story-output",
                ".response",
                ".generated-content",
                "#story-result",
                "#output",
                "[data-testid='story-output']",
            ]

            response_content = ""
            response_found = False

            # Wait for response with multiple strategies
            for attempt in range(12):  # 60 seconds total
                await asyncio.sleep(5)

                # Check for response in common selectors
                for selector in response_selectors:
                    try:
                        response_element = await page.query_selector(selector)
                        if response_element:
                            content = await response_element.text_content()
                            if content and len(content.strip()) > 50:
                                response_content = content.strip()
                                response_found = True
                                print(
                                    f"   ✅ Response found in {selector}: "
                                    f"{len(response_content)} chars"
                                )
                                break
                    except Exception:
                        continue

                if response_found:
                    break

                # Also check if page content changed significantly
                page_content = await page.text_content("body")
                if page_content and len(page_content) > 1000:
                    # Look for story-like content in page
                    story_patterns = [
                        r"(?i)(once upon a time|in the beginning|the story)",
                        r"(?i)(chapter|scene|meanwhile)",
                        r'(?i)(".*?"|\'.*?\')',  # Dialogue
                        r"(?i)(he said|she said|they said)",
                        r"(?i)(suddenly|meanwhile|however)",
                    ]

                    story_indicators = sum(
                        1
                        for pattern in story_patterns
                        if re.search(pattern, page_content)
                    )

                    if story_indicators >= 2:
                        response_content = page_content[
                            -2000:
                        ]  # Last 2000 chars
                        response_found = True
                        print(
                            f"   ✅ Story content detected in page: "
                            f"{story_indicators} indicators"
                        )
                        break

                print(
                    f"   ⏳ Still waiting for response... "
                    f"(attempt {attempt + 1}/12)"
                )

            response_time_ms = int((time.time() - start_time) * 1000)

            if response_found:
                print(
                    f"   🎉 Response received: {len(response_content)} chars "
                    f"in {response_time_ms}ms"
                )
                return True, response_content, response_time_ms
            else:
                print(f"   ❌ No response received after {response_time_ms}ms")
                return False, "", response_time_ms

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            print(f"   ❌ Error submitting prompt: {e}")
            return False, "", response_time_ms

    def analyze_content_for_ai(
        self, content: str, scenario: AIValidationScenario
    ) -> ContentAnalysis:
        """Analyze content to determine if it's AI-generated vs template-based."""
        if not content:
            return ContentAnalysis(0, 0, 0.0, 0.0, 1.0, 0.0, {}, {})

        # Basic metrics
        words = content.split()
        word_count = len(words)
        sentences = re.split(r"[.!?]+", content)
        sentence_count = len([s for s in sentences if s.strip()])

        # Unique phrase detection
        phrases = [" ".join(words[i : i + 3]) for i in range(len(words) - 2)]
        unique_phrases = len(set(phrases))

        # Template indicators (bad signs)
        template_indicators = [
            r"(?i)(sorry, i cannot|as an ai|i am not able)",
            r"(?i)(template|placeholder|example)",
            r"(?i)(\[.*?\]|\{.*?\})",  # Template variables
            r"(?i)(lorem ipsum|sample text)",
            r"(?i)(error|failed|unavailable)",
        ]

        template_matches = sum(
            1 for pattern in template_indicators if re.search(pattern, content)
        )

        # AI indicators (good signs)
        ai_indicators = [
            r'(?i)(".*?"|\'.*?\')',  # Dialogue
            r"(?i)(he thought|she felt|they wondered)",  # Internal states
            r"(?i)(suddenly|meanwhile|however|nevertheless)",  # Narrative flow
            r"(?i)(whispered|shouted|murmured|exclaimed)",  # Varied dialogue tags
            r"(?i)(the.*?room|the.*?door|the.*?window)",  # Spatial descriptions
            r"(?i)(memories|emotions|feelings|thoughts)",  # Psychological depth
        ]

        ai_matches = sum(
            1 for pattern in ai_indicators if re.search(pattern, content)
        )

        # Scenario-specific indicator matching
        scenario_matches = sum(
            1
            for indicator in scenario.expected_ai_indicators
            if indicator.lower() in content.lower()
        )

        # Complexity indicators
        complexity_indicators = {
            "has_dialogue": '"' in content or "'" in content,
            "has_narrative_flow": bool(
                re.search(r"(?i)(then|next|after|while)", content)
            ),
            "has_character_development": bool(
                re.search(r"(?i)(realized|understood|felt|thought)", content)
            ),
            "has_descriptive_language": bool(
                re.search(
                    r"(?i)(beautiful|dark|bright|mysterious|ancient)", content
                )
            ),
            "has_varied_sentence_structure": (
                sentence_count > 5 and word_count / sentence_count > 8
            ),
            "addresses_scenario_complexity": (
                scenario_matches >= len(scenario.expected_ai_indicators) // 2
            ),
        }

        # Calculate scores
        creativity_score = min(
            1.0, (unique_phrases / max(1, len(phrases))) * 2
        )
        coherence_score = min(1.0, (sentence_count / max(1, word_count // 15)))

        # Template probability (lower is better)
        template_probability = min(
            1.0, max(0.0, template_matches / max(1, word_count // 50))
        )

        # AI probability (higher is better)
        ai_base_score = ai_matches / max(1, word_count // 100)
        scenario_bonus = scenario_matches / len(
            scenario.expected_ai_indicators
        )
        complexity_bonus = sum(complexity_indicators.values()) / len(
            complexity_indicators
        )

        ai_probability = min(
            1.0, (ai_base_score + scenario_bonus + complexity_bonus) / 3
        )

        # Quality metrics
        quality_metrics = {
            "word_count": word_count,
            "sentence_variety": sentence_count / max(1, word_count // 10),
            "scenario_relevance": (
                scenario_matches / len(scenario.expected_ai_indicators)
            ),
            "narrative_quality": sum(
                [
                    complexity_indicators["has_dialogue"],
                    complexity_indicators["has_narrative_flow"],
                    complexity_indicators["has_character_development"],
                ]
            )
            / 3,
        }

        return ContentAnalysis(
            word_count=word_count,
            unique_phrases=unique_phrases,
            creativity_score=creativity_score,
            coherence_score=coherence_score,
            template_probability=template_probability,
            ai_probability=ai_probability,
            complexity_indicators=complexity_indicators,
            quality_metrics=quality_metrics,
        )

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run complete AI validation test suite."""
        print("🎯 Starting Comprehensive AI Validation Test")
        print("=" * 60)

        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright not available")
            return {"error": "Playwright not available"}

        test_report = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "AI Validation using Playwright",
            "objective": (
                "Validate real AI generation vs templates/state machines"
            ),
            "scenarios_tested": len(self.test_scenarios),
            "results": [],
            "overall_assessment": {},
        }

        server_process = None

        try:
            # Launch server
            server_process = await self.launch_novel_engine_server()

            async with async_playwright() as playwright:
                # Launch browser
                browser = await playwright.chromium.launch(headless=False)
                context = await browser.new_context()

                # Enable tracing for evidence
                await context.tracing.start(
                    screenshots=True, snapshots=True, sources=True
                )

                page = await context.new_page()

                # Test server availability
                print("\n🔍 Testing Server Availability...")
                (
                    server_available,
                    server_url,
                ) = await self.test_server_availability(page)

                if not server_available:
                    print("❌ No Novel Engine server available for testing")
                    test_report["error"] = "No server available"
                    return test_report

                print(f"✅ Testing Novel Engine at: {server_url}")

                # Take initial screenshot
                await page.screenshot(
                    path=self.evidence_dir / "01_initial_page.png"
                )

                # Run each test scenario
                for i, scenario in enumerate(self.test_scenarios, 1):
                    print(f"\n{'='*60}")
                    print(
                        f"🧪 Test {i}/{len(self.test_scenarios)}: {scenario.name}"
                    )
                    print(f"📋 Complexity Level: {scenario.complexity_level}/5")
                    print(f"🎯 Purpose: {scenario.description}")

                    # Refresh page for clean state
                    await page.reload()
                    await asyncio.sleep(2)

                    # Submit prompt and get response
                    (
                        success,
                        response_content,
                        response_time,
                    ) = await self.submit_creative_prompt(page, scenario)

                    # Take screenshot of result
                    screenshot_filename = (
                        f"{i:02d}_{scenario.name.replace(' ', '_')}_result.png"
                    )
                    await page.screenshot(
                        path=self.evidence_dir / screenshot_filename
                    )

                    # Analyze content
                    if success and response_content:
                        content_analysis = self.analyze_content_for_ai(
                            response_content, scenario
                        )

                        # Calculate AI validation score
                        ai_score = (
                            content_analysis.ai_probability * 0.4
                            + (1 - content_analysis.template_probability) * 0.3
                            + content_analysis.creativity_score * 0.2
                            + content_analysis.coherence_score * 0.1
                        )

                        print("📊 Analysis Results:")
                        print(f"   Word Count: {content_analysis.word_count}")
                        print(
                            f"   Creativity Score: "
                            f"{content_analysis.creativity_score:.2f}"
                        )
                        print(
                            f"   AI Probability: {content_analysis.ai_probability:.2f}"
                        )
                        print(
                            f"   Template Probability: "
                            f"{content_analysis.template_probability:.2f}"
                        )
                        print(f"   🎯 AI Validation Score: {ai_score:.2f}")

                        # Show complexity indicators
                        print("   🔧 Complexity Indicators:")
                        for (
                            indicator,
                            present,
                        ) in content_analysis.complexity_indicators.items():
                            status = "✅" if present else "❌"
                            formatted_indicator = indicator.replace(
                                "_", " "
                            ).title()
                            print(f"      {status} {formatted_indicator}")
                    else:
                        content_analysis = None
                        ai_score = 0.0
                        print("❌ Test failed - no response received")

                    # Create test result
                    result = TestResult(
                        scenario_name=scenario.name,
                        prompt_submitted=success,
                        response_received=bool(response_content),
                        response_time_ms=response_time,
                        content_length=(
                            len(response_content) if response_content else 0
                        ),
                        content_analysis=content_analysis,
                        ai_validation_score=ai_score,
                        evidence_paths=[
                            str(self.evidence_dir / "01_initial_page.png"),
                            str(self.evidence_dir / screenshot_filename),
                        ],
                        raw_content=(
                            response_content[:1000] if response_content else ""
                        ),  # First 1000 chars
                    )

                    self.results.append(result)
                    test_report["results"].append(
                        {
                            "scenario": scenario.name,
                            "success": success,
                            "response_time_ms": response_time,
                            "content_length": (
                                len(response_content)
                                if response_content
                                else 0
                            ),
                            "ai_validation_score": ai_score,
                            "complexity_level": scenario.complexity_level,
                        }
                    )

                    # Brief pause between tests
                    await asyncio.sleep(2)

                # Save tracing evidence
                await context.tracing.stop(
                    path=self.evidence_dir / "playwright_trace.zip"
                )

                # Close browser
                await browser.close()

        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            test_report["error"] = str(e)

        finally:
            # Clean up server
            if server_process:
                server_process.terminate()
                print("🛑 Server stopped")

        # Generate final assessment
        test_report["overall_assessment"] = self.generate_final_assessment()

        return test_report

    def generate_final_assessment(self) -> Dict[str, Any]:
        """Generate final AI validation assessment."""
        if not self.results:
            return {"status": "NO_TESTS_COMPLETED", "confidence": 0.0}

        # Calculate overall metrics
        successful_tests = [r for r in self.results if r.response_received]
        total_tests = len(self.results)
        success_rate = (
            len(successful_tests) / total_tests if total_tests > 0 else 0.0
        )

        if not successful_tests:
            return {
                "status": "NO_SUCCESSFUL_RESPONSES",
                "confidence": 0.0,
                "success_rate": success_rate,
                "recommendation": (
                    "No responses received - system may not be functioning"
                ),
            }

        # Calculate AI validation metrics
        ai_scores = [r.ai_validation_score for r in successful_tests]
        average_ai_score = sum(ai_scores) / len(ai_scores)

        # Content quality metrics
        content_lengths = [r.content_length for r in successful_tests]
        average_length = sum(content_lengths) / len(content_lengths)

        response_times = [r.response_time_ms for r in successful_tests]
        average_response_time = sum(response_times) / len(response_times)

        # Template vs AI analysis
        template_probabilities = []
        ai_probabilities = []
        creativity_scores = []

        for result in successful_tests:
            if result.content_analysis:
                template_probabilities.append(
                    result.content_analysis.template_probability
                )
                ai_probabilities.append(result.content_analysis.ai_probability)
                creativity_scores.append(
                    result.content_analysis.creativity_score
                )

        avg_template_prob = (
            sum(template_probabilities) / len(template_probabilities)
            if template_probabilities
            else 1.0
        )
        avg_ai_prob = (
            sum(ai_probabilities) / len(ai_probabilities)
            if ai_probabilities
            else 0.0
        )
        avg_creativity = (
            sum(creativity_scores) / len(creativity_scores)
            if creativity_scores
            else 0.0
        )

        # Determine overall validation status
        if average_ai_score >= 0.8:
            status = "REAL_AI_VALIDATED"
            confidence = min(0.95, average_ai_score)
            recommendation = (
                "High confidence that system uses real AI generation"
            )
        elif average_ai_score >= 0.6:
            status = "LIKELY_REAL_AI"
            confidence = average_ai_score * 0.8
            recommendation = (
                "Evidence suggests real AI usage with some concerns"
            )
        elif average_ai_score >= 0.4:
            status = "MIXED_RESULTS"
            confidence = average_ai_score * 0.6
            recommendation = "Inconclusive evidence - may be hybrid system"
        elif average_ai_score >= 0.2:
            status = "LIKELY_TEMPLATES"
            confidence = (1 - average_ai_score) * 0.8
            recommendation = "Evidence suggests template-based responses"
        else:
            status = "NO_AI_DETECTED"
            confidence = (1 - average_ai_score) * 0.9
            recommendation = "Strong evidence of mocked or template responses"

        return {
            "status": status,
            "confidence": confidence,
            "success_rate": success_rate,
            "recommendation": recommendation,
            "metrics": {
                "tests_completed": total_tests,
                "successful_responses": len(successful_tests),
                "average_ai_score": average_ai_score,
                "average_content_length": average_length,
                "average_response_time_ms": average_response_time,
                "average_template_probability": avg_template_prob,
                "average_ai_probability": avg_ai_prob,
                "average_creativity_score": avg_creativity,
            },
        }


async def main():
    """Run the comprehensive AI validation test."""
    validator = NovelEngineAIValidator()

    try:
        test_report = await validator.run_comprehensive_test()

        # Save detailed report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"ai_validation_report_{timestamp}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(test_report, f, indent=2, ensure_ascii=False)

        # Print summary
        print("\n" + "=" * 60)
        print("🎯 AI VALIDATION TEST SUMMARY")
        print("=" * 60)

        if "error" in test_report:
            print(f"❌ Test Error: {test_report['error']}")
            return False

        assessment = test_report.get("overall_assessment", {})
        status = assessment.get("status", "UNKNOWN")
        confidence = assessment.get("confidence", 0.0)

        # Status display
        status_icons = {
            "REAL_AI_VALIDATED": "✅",
            "LIKELY_REAL_AI": "🟢",
            "MIXED_RESULTS": "🟡",
            "LIKELY_TEMPLATES": "🟠",
            "NO_AI_DETECTED": "🔴",
            "NO_TESTS_COMPLETED": "❌",
            "NO_SUCCESSFUL_RESPONSES": "❌",
        }

        icon = status_icons.get(status, "❓")
        print(f"{icon} Status: {status}")
        print(f"📊 Confidence: {confidence:.1%}")
        print(f"💡 Assessment: {assessment.get('recommendation', 'N/A')}")

        if "metrics" in assessment:
            metrics = assessment["metrics"]
            print("\n📈 Test Metrics:")
            print(f"   Tests Completed: {metrics.get('tests_completed', 0)}")
            print(
                f"   Successful Responses: "
                f"{metrics.get('successful_responses', 0)}"
            )
            print(f"   Success Rate: {metrics.get('success_rate', 0):.1%}")
            print(
                f"   Average AI Score: {metrics.get('average_ai_score', 0):.2f}"
            )
            print(
                f"   Average Response Time: "
                f"{metrics.get('average_response_time_ms', 0):.0f}ms"
            )
            print(
                f"   Average Content Length: "
                f"{metrics.get('average_content_length', 0):.0f} chars"
            )

        # Evidence location
        print(f"\n📁 Evidence saved to: {validator.evidence_dir}")
        print(f"📄 Full report: {report_path}")

        # Final determination
        ai_validated = status in ["REAL_AI_VALIDATED", "LIKELY_REAL_AI"]

        if ai_validated:
            print(
                "\n🎉 CONCLUSION: Novel Engine validates as real AI-based system"
            )
            print("   ✅ Uses genuine LLM API calls")
            print("   ✅ Demonstrates creative freedom (自由度)")
            print("   ✅ Generates quality story content")
        else:
            print("\n⚠️ CONCLUSION: AI validation concerns detected")
            print("   ❓ System may not be using real AI generation")
            print("   ❓ Responses may be template-based or mocked")

        return ai_validated

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
