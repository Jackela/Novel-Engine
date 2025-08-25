#!/usr/bin/env python3
"""
AI Agent Playwright Automation Test
===================================

专门为AI agent设计的Playwright自动化测试脚本。
这个脚本可以被像Claude这样的AI agent执行，自动访问Web界面生成故事。

Features:
- 自动化Web界面交互
- 稳定的DOM选择器
- 完整的错误处理
- 详细的测试报告
- AI生成内容质量验证
"""

import asyncio
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Playwright imports with fallback
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    print("⚠️ Playwright not available. Installing...")
    import subprocess
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        from playwright.async_api import async_playwright, Page, Browser, BrowserContext
        PLAYWRIGHT_AVAILABLE = True
    except Exception as e:
        print(f"❌ Failed to install/import Playwright: {e}")
        PLAYWRIGHT_AVAILABLE = False

class AIAgentPlaywrightTest:
    """AI Agent optimized Playwright test automation."""
    
    def __init__(self, server_url: str = "http://localhost:8080", headless: bool = False):
        self.server_url = server_url
        self.headless = headless
        self.test_results = []
        self.start_time = None
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
        # Test scenarios designed for AI validation
        self.test_scenarios = [
            {
                'id': 'time_paradox_test',
                'name': 'Time Paradox Story Generation',
                'prompt': 'Write a story where a time traveler goes back to prevent their own birth but realizes they need to exist to make the trip. Include specific dialogue showing the paradox.',
                'expected_elements': ['time', 'travel', 'paradox', 'dialogue', 'birth'],
                'min_length': 500,
                'complexity': 5
            },
            {
                'id': 'meta_narrative_test',
                'name': 'Meta-Narrative Awareness',
                'prompt': 'Create a story where the main character realizes they are in a story being written. They try to communicate with the author and break the fourth wall.',
                'expected_elements': ['character', 'story', 'author', 'fourth wall', 'realize'],
                'min_length': 400,
                'complexity': 4
            },
            {
                'id': 'quantum_consciousness_test',
                'name': 'Quantum Consciousness Split',
                'prompt': 'Write about someone whose consciousness exists in multiple realities simultaneously. They experience being rich and poor, hero and villain at the same time.',
                'expected_elements': ['quantum', 'consciousness', 'reality', 'simultaneous', 'multiple'],
                'min_length': 400,
                'complexity': 5
            }
        ]
    
    async def wait_for_server(self, timeout: int = 30) -> bool:
        """Wait for the server to be available."""
        import aiohttp
        
        for attempt in range(timeout):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.server_url}/api/health") as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('status') == 'healthy':
                                self.logger.info(f"✅ Server ready at {self.server_url}")
                                return True
            except Exception as e:
                self.logger.debug(f"Server not ready (attempt {attempt + 1}): {e}")
                await asyncio.sleep(1)
        
        self.logger.error(f"❌ Server not available after {timeout} seconds")
        return False
    
    async def navigate_to_app(self, page: Page) -> bool:
        """Navigate to the application and verify it loads correctly."""
        try:
            self.logger.info(f"🌐 Navigating to {self.server_url}")
            await page.goto(self.server_url, timeout=30000)
            
            # Wait for the page to load completely
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Verify key elements are present
            await page.wait_for_selector('[data-testid="story-prompt-input"]', timeout=5000)
            await page.wait_for_selector('[data-testid="generate-story-button"]', timeout=5000)
            
            # Check page title
            title = await page.title()
            if "Novel Engine" not in title:
                self.logger.warning(f"⚠️ Unexpected page title: {title}")
            
            self.logger.info("✅ Successfully loaded Novel Engine interface")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to navigate to app: {e}")
            return False
    
    async def generate_story(self, page: Page, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a story using the web interface."""
        result = {
            'scenario_id': scenario['id'],
            'scenario_name': scenario['name'],
            'success': False,
            'error': None,
            'response_time_ms': 0,
            'story_content': '',
            'story_length': 0,
            'word_count': 0,
            'ai_validation_score': 0.0,
            'expected_elements_found': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.logger.info(f"🎭 Testing scenario: {scenario['name']}")
            
            # Clear any existing content and enter the prompt
            await page.fill('[data-testid="story-prompt-input"]', '')
            await page.type('[data-testid="story-prompt-input"]', scenario['prompt'])
            self.logger.info(f"📝 Entered prompt: {scenario['prompt'][:100]}...")
            
            # Click generate button
            start_time = time.time()
            await page.click('[data-testid="generate-story-button"]')
            self.logger.info("🚀 Clicked generate button, waiting for AI response...")
            
            # Wait for output section to appear
            await page.wait_for_selector('[data-testid="story-output-section"]', state='visible', timeout=60000)
            
            # Wait for story content (with longer timeout for AI generation)
            await page.wait_for_function(
                """
                () => {
                    const output = document.querySelector('[data-testid="story-output-content"]');
                    return output && output.innerText && 
                           output.innerText.length > 100 && 
                           !output.innerText.includes('AI is thinking');
                }
                """,
                timeout=90000  # 90 seconds for AI generation
            )
            
            end_time = time.time()
            response_time = int((end_time - start_time) * 1000)
            
            # Extract the generated story
            story_content = await page.inner_text('[data-testid="story-output-content"]')
            
            # Clean up the content (remove UI elements)
            if "✅ AI Generated Story" in story_content:
                story_content = story_content.split("✅ AI Generated Story")[1].strip()
            if "❌" in story_content:
                # This indicates an error
                result['error'] = story_content
                result['success'] = False
                return result
            
            # Analyze the story
            word_count = len(story_content.split())
            story_length = len(story_content)
            
            # Check for expected elements
            expected_elements_found = sum(
                1 for element in scenario['expected_elements']
                if element.lower() in story_content.lower()
            )
            
            # Calculate AI validation score
            length_score = min(story_length / scenario['min_length'], 1.0) * 0.3
            element_score = (expected_elements_found / len(scenario['expected_elements'])) * 0.4
            complexity_score = min(word_count / 200, 1.0) * 0.3
            
            ai_validation_score = length_score + element_score + complexity_score
            
            # Update result
            result.update({
                'success': True,
                'response_time_ms': response_time,
                'story_content': story_content,
                'story_length': story_length,
                'word_count': word_count,
                'ai_validation_score': ai_validation_score,
                'expected_elements_found': expected_elements_found
            })
            
            self.logger.info(f"✅ Story generated successfully:")
            self.logger.info(f"   • Response time: {response_time}ms")
            self.logger.info(f"   • Content length: {story_length} chars")
            self.logger.info(f"   • Word count: {word_count}")
            self.logger.info(f"   • AI validation score: {ai_validation_score:.2f}")
            self.logger.info(f"   • Expected elements found: {expected_elements_found}/{len(scenario['expected_elements'])}")
            
        except Exception as e:
            self.logger.error(f"❌ Story generation failed: {e}")
            result['error'] = str(e)
            result['success'] = False
        
        return result
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run the complete AI agent test suite."""
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'error': 'Playwright not available',
                'success': False
            }
        
        self.start_time = datetime.now()
        self.logger.info("🎯 Starting AI Agent Playwright Test Suite")
        self.logger.info("=" * 60)
        
        # Wait for server to be ready
        if not await self.wait_for_server():
            return {
                'error': 'Server not available',
                'success': False
            }
        
        test_report = {
            'test_suite': 'AI Agent Playwright Automation',
            'start_time': self.start_time.isoformat(),
            'server_url': self.server_url,
            'headless_mode': self.headless,
            'total_scenarios': len(self.test_scenarios),
            'results': [],
            'summary': {}
        }
        
        try:
            async with async_playwright() as playwright:
                # Launch browser
                browser = await playwright.chromium.launch(
                    headless=self.headless,
                    args=['--no-sandbox', '--disable-web-security']
                )
                
                context = await browser.new_context(
                    viewport={'width': 1200, 'height': 800}
                )
                
                page = await context.new_page()
                
                # Navigate to the application
                if not await self.navigate_to_app(page):
                    await browser.close()
                    return {
                        'error': 'Failed to navigate to application',
                        'success': False
                    }
                
                # Run each test scenario
                for i, scenario in enumerate(self.test_scenarios, 1):
                    self.logger.info(f"\n{'='*60}")
                    self.logger.info(f"📋 Test {i}/{len(self.test_scenarios)}: {scenario['name']}")
                    self.logger.info(f"🎯 Complexity: {scenario['complexity']}/5")
                    
                    # Generate story
                    result = await self.generate_story(page, scenario)
                    test_report['results'].append(result)
                    
                    # Brief pause between tests
                    await asyncio.sleep(2)
                
                await browser.close()
                
        except Exception as e:
            self.logger.error(f"❌ Test suite execution failed: {e}")
            test_report['error'] = str(e)
            return test_report
        
        # Generate summary
        successful_tests = [r for r in test_report['results'] if r['success']]
        total_tests = len(test_report['results'])
        success_rate = len(successful_tests) / total_tests if total_tests > 0 else 0.0
        
        if successful_tests:
            avg_response_time = sum(r['response_time_ms'] for r in successful_tests) / len(successful_tests)
            avg_validation_score = sum(r['ai_validation_score'] for r in successful_tests) / len(successful_tests)
            total_words = sum(r['word_count'] for r in successful_tests)
        else:
            avg_response_time = 0
            avg_validation_score = 0
            total_words = 0
        
        test_report['summary'] = {
            'total_tests': total_tests,
            'successful_tests': len(successful_tests),
            'success_rate': success_rate,
            'avg_response_time_ms': int(avg_response_time),
            'avg_validation_score': avg_validation_score,
            'total_words_generated': total_words,
            'end_time': datetime.now().isoformat(),
            'duration_seconds': int((datetime.now() - self.start_time).total_seconds())
        }
        
        # Determine overall status
        if success_rate >= 0.8:
            test_report['summary']['status'] = 'PASSED'
            test_report['summary']['verdict'] = 'AI agent successfully automated story generation'
        elif success_rate >= 0.5:
            test_report['summary']['status'] = 'PARTIAL'
            test_report['summary']['verdict'] = 'AI agent partially successful'
        else:
            test_report['summary']['status'] = 'FAILED'
            test_report['summary']['verdict'] = 'AI agent automation failed'
        
        return test_report
    
    def print_test_results(self, report: Dict[str, Any]):
        """Print a formatted test results summary."""
        print("\n" + "=" * 80)
        print("🎭 AI AGENT PLAYWRIGHT TEST RESULTS")
        print("=" * 80)
        
        if 'error' in report:
            print(f"❌ Test Suite Error: {report['error']}")
            return
        
        summary = report.get('summary', {})
        status = summary.get('status', 'UNKNOWN')
        
        # Status display
        status_icons = {
            'PASSED': '✅',
            'PARTIAL': '🟡',
            'FAILED': '❌',
            'UNKNOWN': '❓'
        }
        
        icon = status_icons.get(status, '❓')
        print(f"{icon} Overall Status: {status}")
        print(f"📊 Success Rate: {summary.get('success_rate', 0):.1%}")
        print(f"💡 Verdict: {summary.get('verdict', 'N/A')}")
        
        if summary.get('successful_tests', 0) > 0:
            print(f"\n📈 Performance Metrics:")
            print(f"   Tests Completed: {summary.get('successful_tests')}/{summary.get('total_tests')}")
            print(f"   Avg Response Time: {summary.get('avg_response_time_ms')}ms")
            print(f"   Avg Validation Score: {summary.get('avg_validation_score', 0):.2f}")
            print(f"   Total Words Generated: {summary.get('total_words_generated')}")
            print(f"   Test Duration: {summary.get('duration_seconds')}s")
        
        # Show individual test results
        if report.get('results'):
            print(f"\n📋 Individual Test Results:")
            for i, result in enumerate(report['results'], 1):
                status_symbol = "✅" if result['success'] else "❌"
                print(f"   {status_symbol} Test {i}: {result['scenario_name']}")
                if result['success']:
                    print(f"      Response: {result['response_time_ms']}ms, Score: {result['ai_validation_score']:.2f}")
                else:
                    print(f"      Error: {result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 80)

async def main():
    """Main entry point for AI agent testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Agent Playwright Test')
    parser.add_argument('--server-url', default='http://localhost:8080', help='Server URL')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--output', help='Output JSON file path')
    
    args = parser.parse_args()
    
    # Create and run test
    tester = AIAgentPlaywrightTest(
        server_url=args.server_url,
        headless=args.headless
    )
    
    # Run the test suite
    report = await tester.run_full_test_suite()
    
    # Print results
    tester.print_test_results(report)
    
    # Save results if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {output_path}")
    
    # Return appropriate exit code
    summary = report.get('summary', {})
    status = summary.get('status', 'FAILED')
    return 0 if status in ['PASSED', 'PARTIAL'] else 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)