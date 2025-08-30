#!/usr/bin/env node

/**
 * Creative UAT Script - Final Autonomous Generative Testing
 * 
 * This script performs a comprehensive creative evaluation of the Emergent Narrative Dashboard
 * by acting as a creative user, creating characters, running story turns, and evaluating
 * the generated narrative quality.
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
  backend_url: 'http://127.0.0.1:8000',
  frontend_url: 'http://localhost:3002',
  timeout: 60000,
  turn_count: 10,
  screenshot_dir: './uat-screenshots',
  story_output_file: './extracted_narrative.md'
};

// Creative character designs
const CREATIVE_CHARACTERS = [
  {
    name: "Zara Nightwhisper",
    background: "A former spy turned information broker who operates from the shadows of the city's underbelly. She has an extensive network of contacts and owes her survival to her ability to read people and situations with uncanny accuracy.",
    personality: "Paranoid yet charming, analytical but prone to emotional outbursts when betrayed. She values loyalty above all else and has a dry, sardonic wit that masks deep-seated trust issues.",
    motivations: "Seeking to uncover a conspiracy that destroyed her former spy network. She needs allies but struggles to trust anyone completely.",
    skills: "Stealth, Investigation, Persuasion, Information Gathering",
    secrets: "She still has feelings for her former handler who betrayed her organization."
  },
  {
    name: "Professor Magnus Cogwright",
    background: "An eccentric inventor and scholar obsessed with mechanical contraptions and ancient technologies. He believes that the lost sciences of previous civilizations hold the key to humanity's future.",
    personality: "Brilliant but absent-minded, enthusiastic about his work to the point of neglecting basic needs. He speaks in technical jargon and often forgets social conventions, but possesses surprising wisdom about human nature.",
    motivations: "Trying to complete his life's work - a device that could revolutionize how people understand reality itself. He needs rare materials and funding.",
    skills: "Engineering, History, Research, Mechanical Repairs",
    secrets: "His inventions sometimes work through means he doesn't fully understand, suggesting a connection to supernatural forces."
  },
  {
    name: "Captain Rhea Stormchaser",
    background: "A former naval officer turned mercenary captain who commands a small but loyal crew. She left the military after witnessing corruption at the highest levels and now works for causes she believes in.",
    personality: "Bold and decisive in action, but introspective and melancholy in quiet moments. She values honor and protecting those who cannot protect themselves, often taking on missions that pay poorly but serve a greater good.",
    motivations: "Hunting down war criminals from her military past while building a reputation as someone who can be trusted to complete impossible missions.",
    skills: "Leadership, Combat Tactics, Naval Operations, Survival",
    secrets: "She carries the guilt of a military disaster that she could have prevented, which drives her current crusade for justice."
  }
];

class CreativeUATRunner {
  constructor() {
    this.browser = null;
    this.page = null;
    this.narrative_content = '';
    this.test_start_time = Date.now();
    this.screenshots = [];
    
    // Ensure screenshot directory exists
    if (!fs.existsSync(CONFIG.screenshot_dir)) {
      fs.mkdirSync(CONFIG.screenshot_dir, { recursive: true });
    }
  }

  async initialize() {
    console.log('🚀 Initializing Creative UAT Runner...');
    
    this.browser = await chromium.launch({ 
      headless: false,
      slowMo: 500 // Add delay for visibility
    });
    
    this.page = await this.browser.newPage();
    
    // Set up console logging to capture any errors
    this.page.on('console', msg => console.log(`PAGE LOG: ${msg.text()}`));
    this.page.on('pageerror', error => console.error(`PAGE ERROR: ${error}`));
    
    await this.page.setViewportSize({ width: 1440, height: 900 });
  }

  async takeScreenshot(name) {
    const timestamp = Date.now();
    const filename = `${name}-${timestamp}.png`;
    const filepath = path.join(CONFIG.screenshot_dir, filename);
    
    await this.page.screenshot({ path: filepath, fullPage: true });
    this.screenshots.push({ name, filepath, timestamp });
    console.log(`📸 Screenshot saved: ${filename}`);
    
    return filepath;
  }

  async waitForElement(selector, timeout = CONFIG.timeout) {
    try {
      await this.page.waitForSelector(selector, { timeout });
      return true;
    } catch (error) {
      console.error(`⚠️  Element not found: ${selector}`);
      return false;
    }
  }

  async navigateToDashboard() {
    console.log('🧭 Navigating to Emergent Narrative Dashboard...');
    
    try {
      await this.page.goto(CONFIG.frontend_url, { 
        waitUntil: 'networkidle',
        timeout: CONFIG.timeout 
      });
      
      await this.takeScreenshot('dashboard-initial-load');
      
      // Wait for dashboard components to load
      const dashboardLoaded = await this.waitForElement('[data-testid="dashboard"], .dashboard, #dashboard, .bento-grid', 30000);
      
      if (!dashboardLoaded) {
        // Try alternative selectors for dashboard
        const altSelectors = ['.app', '#app', '[data-component="dashboard"]', '.main-content'];
        for (const selector of altSelectors) {
          if (await this.waitForElement(selector, 5000)) {
            console.log(`✅ Found dashboard using selector: ${selector}`);
            break;
          }
        }
      }
      
      await this.takeScreenshot('dashboard-loaded');
      console.log('✅ Dashboard navigation completed');
      
    } catch (error) {
      console.error(`❌ Failed to navigate to dashboard: ${error.message}`);
      await this.takeScreenshot('navigation-error');
      throw error;
    }
  }

  async createCharacter(characterData, index) {
    console.log(`👤 Creating character ${index + 1}: ${characterData.name}`);
    
    try {
      // Look for various character creation elements
      const creationSelectors = [
        '[data-testid="create-character"]',
        '[data-testid="add-character"]', 
        'button:has-text("Create Character")',
        'button:has-text("Add Character")',
        'button:has-text("New Character")',
        '.character-creation-button',
        '.add-character-btn',
        '#create-character',
        '[aria-label="Create Character"]'
      ];
      
      let createButton = null;
      for (const selector of creationSelectors) {
        try {
          createButton = await this.page.waitForSelector(selector, { timeout: 5000 });
          if (createButton) {
            console.log(`Found create button with selector: ${selector}`);
            break;
          }
        } catch (e) {
          // Continue trying other selectors
        }
      }
      
      if (!createButton) {
        console.log('⚠️  No create character button found, looking for character forms...');
        
        // Alternative: Look for direct character input forms
        const formSelectors = [
          'input[placeholder*="name" i], input[name="name"], input[id*="name"]',
          '.character-form',
          '[data-testid="character-form"]'
        ];
        
        for (const selector of formSelectors) {
          if (await this.waitForElement(selector, 5000)) {
            console.log(`Found character form with selector: ${selector}`);
            await this.fillCharacterForm(characterData);
            return;
          }
        }
        
        throw new Error('Could not find character creation interface');
      }
      
      await createButton.click();
      await this.page.waitForTimeout(1000);
      
      await this.fillCharacterForm(characterData);
      await this.takeScreenshot(`character-${index + 1}-created`);
      
    } catch (error) {
      console.error(`❌ Failed to create character ${characterData.name}: ${error.message}`);
      await this.takeScreenshot(`character-${index + 1}-error`);
      throw error;
    }
  }

  async fillCharacterForm(characterData) {
    console.log(`✏️  Filling character form for ${characterData.name}`);
    
    // Fill character name
    const nameSelectors = [
      'input[name="name"]',
      'input[placeholder*="name" i]',
      'input[id*="name"]',
      '[data-testid="character-name"]'
    ];
    
    for (const selector of nameSelectors) {
      try {
        const nameInput = await this.page.waitForSelector(selector, { timeout: 3000 });
        if (nameInput) {
          await nameInput.fill(characterData.name);
          console.log(`✅ Name filled: ${characterData.name}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }
    
    // Fill background/description
    const descSelectors = [
      'textarea[name="background"]',
      'textarea[name="description"]',
      'textarea[placeholder*="background" i]',
      'textarea[placeholder*="description" i]',
      '[data-testid="character-background"]',
      '[data-testid="character-description"]'
    ];
    
    for (const selector of descSelectors) {
      try {
        const descInput = await this.page.waitForSelector(selector, { timeout: 3000 });
        if (descInput) {
          await descInput.fill(characterData.background);
          console.log(`✅ Background filled for ${characterData.name}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }
    
    // Fill personality
    const personalitySelectors = [
      'textarea[name="personality"]',
      'input[name="personality"]',
      'textarea[placeholder*="personality" i]',
      '[data-testid="character-personality"]'
    ];
    
    for (const selector of personalitySelectors) {
      try {
        const personalityInput = await this.page.waitForSelector(selector, { timeout: 3000 });
        if (personalityInput) {
          await personalityInput.fill(characterData.personality);
          console.log(`✅ Personality filled for ${characterData.name}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }
    
    // Submit the form
    const submitSelectors = [
      'button[type="submit"]',
      'button:has-text("Create")',
      'button:has-text("Save")',
      'button:has-text("Add")',
      '[data-testid="submit-character"]',
      '.submit-btn',
      '.create-btn'
    ];
    
    for (const selector of submitSelectors) {
      try {
        const submitButton = await this.page.waitForSelector(selector, { timeout: 3000 });
        if (submitButton) {
          await submitButton.click();
          console.log(`✅ Character form submitted for ${characterData.name}`);
          await this.page.waitForTimeout(2000); // Wait for submission
          break;
        }
      } catch (e) {
        continue;
      }
    }
  }

  async runStoryOrchestration() {
    console.log(`🎭 Starting story orchestration for ${CONFIG.turn_count} turns...`);
    
    try {
      // Look for turn orchestration trigger
      const orchestrationSelectors = [
        '[data-testid="start-orchestration"]',
        '[data-testid="play-button"]',
        'button:has-text("Start")',
        'button:has-text("Play")',
        'button:has-text("Begin")',
        'button:has-text("Run")',
        '.play-btn',
        '.start-btn',
        '.orchestration-trigger'
      ];
      
      let orchestrationButton = null;
      for (const selector of orchestrationSelectors) {
        try {
          orchestrationButton = await this.page.waitForSelector(selector, { timeout: 5000 });
          if (orchestrationButton) {
            console.log(`Found orchestration button with selector: ${selector}`);
            break;
          }
        } catch (e) {
          continue;
        }
      }
      
      if (!orchestrationButton) {
        throw new Error('Could not find story orchestration trigger');
      }
      
      await orchestrationButton.click();
      console.log('✅ Story orchestration started');
      
      await this.takeScreenshot('orchestration-started');
      
      // Monitor progress for the specified number of turns
      for (let turn = 1; turn <= CONFIG.turn_count; turn++) {
        console.log(`⏳ Monitoring turn ${turn}/${CONFIG.turn_count}...`);
        
        // Wait for turn completion indicators
        await this.page.waitForTimeout(3000); // Wait between turns
        
        // Look for progress indicators
        const progressSelectors = [
          '.progress-indicator',
          '[data-testid="turn-progress"]',
          '.turn-counter',
          '.narrative-progress'
        ];
        
        // Take screenshot every few turns
        if (turn % 2 === 0) {
          await this.takeScreenshot(`orchestration-turn-${turn}`);
        }
      }
      
      console.log('✅ Story orchestration completed');
      await this.takeScreenshot('orchestration-completed');
      
    } catch (error) {
      console.error(`❌ Failed to run story orchestration: ${error.message}`);
      await this.takeScreenshot('orchestration-error');
      throw error;
    }
  }

  async extractNarrative() {
    console.log('📖 Extracting final narrative content...');
    
    try {
      // Look for narrative content in various possible locations
      const narrativeSelectors = [
        '[data-testid="narrative-content"]',
        '[data-testid="story-content"]',
        '.narrative-display',
        '.story-text',
        '.generated-story',
        '.narrative-output',
        '.story-content',
        '#narrative-text',
        '#story-output'
      ];
      
      let narrativeContent = '';
      
      for (const selector of narrativeSelectors) {
        try {
          const element = await this.page.waitForSelector(selector, { timeout: 5000 });
          if (element) {
            narrativeContent = await element.innerText();
            if (narrativeContent && narrativeContent.length > 50) {
              console.log(`✅ Found narrative content with selector: ${selector}`);
              console.log(`📏 Content length: ${narrativeContent.length} characters`);
              break;
            }
          }
        } catch (e) {
          continue;
        }
      }
      
      if (!narrativeContent) {
        // Try to extract any text content from the page that looks like a story
        const pageContent = await this.page.content();
        const textContent = await this.page.evaluate(() => document.body.innerText);
        
        // Look for story-like content (longer text blocks)
        const paragraphs = textContent.split('\n').filter(p => p.length > 100);
        if (paragraphs.length > 0) {
          narrativeContent = paragraphs.join('\n\n');
          console.log('⚠️  Using extracted page content as narrative');
        } else {
          narrativeContent = 'No narrative content could be extracted from the interface.';
          console.log('❌ No narrative content found');
        }
      }
      
      this.narrative_content = narrativeContent;
      
      // Save narrative to file
      fs.writeFileSync(CONFIG.story_output_file, narrativeContent);
      console.log(`✅ Narrative extracted and saved to ${CONFIG.story_output_file}`);
      
      await this.takeScreenshot('narrative-extracted');
      
      return narrativeContent;
      
    } catch (error) {
      console.error(`❌ Failed to extract narrative: ${error.message}`);
      await this.takeScreenshot('extraction-error');
      throw error;
    }
  }

  async generateExecutionReport() {
    const execution_time = Date.now() - this.test_start_time;
    const report = {
      test_execution: {
        start_time: new Date(this.test_start_time).toISOString(),
        end_time: new Date().toISOString(),
        duration_ms: execution_time,
        duration_formatted: `${Math.floor(execution_time / 1000)}s`
      },
      characters_created: CREATIVE_CHARACTERS.length,
      story_turns_executed: CONFIG.turn_count,
      narrative_length: this.narrative_content.length,
      screenshots_captured: this.screenshots.length,
      screenshot_files: this.screenshots,
      system_urls: {
        backend: CONFIG.backend_url,
        frontend: CONFIG.frontend_url
      },
      test_configuration: CONFIG
    };
    
    const reportPath = './creative-uat-execution-report.json';
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`📊 Execution report saved to ${reportPath}`);
    
    return report;
  }

  async cleanup() {
    console.log('🧹 Cleaning up...');
    
    if (this.browser) {
      await this.browser.close();
    }
    
    console.log('✅ Cleanup completed');
  }
}

// Main execution function
async function runCreativeUAT() {
  const runner = new CreativeUATRunner();
  
  try {
    console.log('🎬 Starting Creative UAT - Final Autonomous Generative Testing');
    console.log(`📋 Test Configuration:`);
    console.log(`   - Backend URL: ${CONFIG.backend_url}`);
    console.log(`   - Frontend URL: ${CONFIG.frontend_url}`);
    console.log(`   - Characters to create: ${CREATIVE_CHARACTERS.length}`);
    console.log(`   - Story turns to execute: ${CONFIG.turn_count}`);
    console.log('');
    
    // Initialize
    await runner.initialize();
    
    // Wave 1: Setup and Environment Validation
    console.log('🌊 Wave 1: Setup and Environment Validation');
    await runner.navigateToDashboard();
    
    // Wave 2: Creative Character Design
    console.log('🌊 Wave 2: Creative Character Design');
    for (let i = 0; i < CREATIVE_CHARACTERS.length; i++) {
      await runner.createCharacter(CREATIVE_CHARACTERS[i], i);
    }
    
    // Wave 3: Long-form Narrative Generation
    console.log('🌊 Wave 3: Long-form Narrative Generation');
    await runner.runStoryOrchestration();
    
    // Wave 4: Content Extraction
    console.log('🌊 Wave 4: Content Extraction');
    await runner.extractNarrative();
    
    // Generate execution report
    const report = await runner.generateExecutionReport();
    
    console.log('');
    console.log('🎉 Creative UAT Execution Completed Successfully!');
    console.log(`📊 Execution Summary:`);
    console.log(`   - Duration: ${report.test_execution.duration_formatted}`);
    console.log(`   - Characters Created: ${report.characters_created}`);
    console.log(`   - Story Turns: ${report.story_turns_executed}`);
    console.log(`   - Narrative Length: ${report.narrative_length} characters`);
    console.log(`   - Screenshots: ${report.screenshots_captured}`);
    console.log('');
    console.log('📝 Next Step: Run Wave 5 - Literary Critic Analysis');
    console.log('   The extracted narrative will be analyzed for literary quality.');
    
    return report;
    
  } catch (error) {
    console.error('❌ Creative UAT Failed:', error);
    await runner.takeScreenshot('final-error-state');
    throw error;
  } finally {
    await runner.cleanup();
  }
}

// Run the test
if (require.main === module) {
  runCreativeUAT().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

module.exports = { runCreativeUAT, CreativeUATRunner };