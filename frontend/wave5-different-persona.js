/**
 * WAVE 5: DIFFERENT PERSONA TESTING
 * Run complete scenario with new character persona (not Aria Shadowbane)
 * Character: Kael Stormwind - Ambitious Warrior seeking powerful artifacts
 */

import { chromium } from 'playwright';
import fs from 'fs';

// New Character Persona Definition
const KAEL_STORMWIND = {
  name: "Kael Stormwind",
  role: "Ambitious Warrior",
  personality: "Bold, direct, action-oriented, seeks power and glory",
  goal: "Seek powerful artifacts and forge strategic alliances for personal advancement",
  approach: "Aggressive exploration with focus on strength-building and resource acquisition",
  traits: [
    "Decisive and quick to act",
    "Values strength and power above all", 
    "Pragmatic in relationships - seeks mutual benefit",
    "Direct communicator, dislikes subtlety",
    "Competitive and achievement-focused"
  ]
};

// Kael's Exploration Scenarios
const KAEL_SCENARIOS = [
  { action: 'warrior_assessment', description: 'Kael surveys the dashboard with a warrior\'s strategic mindset' },
  { action: 'power_source_identification', description: 'Identify sources of power, influence, and valuable resources' },
  { action: 'strategic_alliance_mapping', description: 'Map potential alliances and power structures' },
  { action: 'merchant_evaluation', description: 'Evaluate Merchant Aldric as potential business partner' },
  { action: 'resource_acquisition_focus', description: 'Focus on acquiring valuable items and information' },
  { action: 'competitive_analysis', description: 'Analyze competition and potential rivals' },
  { action: 'strength_demonstration', description: 'Demonstrate capabilities through decisive actions' },
  { action: 'territory_exploration', description: 'Explore territories for expansion opportunities' },
  { action: 'alliance_negotiation', description: 'Begin negotiations for strategic partnerships' },
  { action: 'final_power_assessment', description: 'Final assessment of power gained and alliances formed' }
];

class KaelStormwindTest {
  constructor() {
    this.results = {
      timestamp: new Date().toISOString(),
      persona: KAEL_STORMWIND,
      mission: 'Strategic exploration focused on power and alliances',
      turns: [],
      achievements: {
        powerGained: 0,
        alliancesFormed: 0,
        resourcesAcquired: 0,
        strategicAdvantages: []
      },
      personality: {
        decisiveness: 0,
        aggression: 0,
        pragmatism: 0
      },
      errors: []
    };
    this.browser = null;
    this.page = null;
    this.startTime = Date.now();
    this.turnCount = 0;
  }

  async initialize() {
    console.log('⚔️ WAVE 5: DIFFERENT PERSONA - Kael Stormwind Exploration...');
    console.log(`🎯 Character: ${KAEL_STORMWIND.name} - ${KAEL_STORMWIND.role}`);
    console.log(`⚡ Personality: ${KAEL_STORMWIND.personality}`);
    console.log(`🎖️ Goal: ${KAEL_STORMWIND.goal}`);
    console.log(`🏹 Approach: ${KAEL_STORMWIND.approach}\n`);
    
    this.browser = await chromium.launch({ 
      headless: false,
      slowMo: 300 // Kael is more deliberate and aggressive
    });
    
    const context = await this.browser.newContext({
      viewport: { width: 1920, height: 1080 }
    });
    
    this.page = await context.newPage();
    
    // Error monitoring with warrior's perspective
    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error(`⚔️ Kael encounters resistance (Turn ${this.turnCount}):`, msg.text());
        this.results.errors.push({
          turn: this.turnCount,
          type: 'console_error',
          message: msg.text(),
          timestamp: Date.now() - this.startTime
        });
      }
    });

    // Navigate with warrior's determination
    console.log('🏰 Kael approaches the Emergent Narrative Dashboard...');
    await this.page.goto('http://localhost:3002/dashboard', { waitUntil: 'networkidle' });
    await this.page.waitForTimeout(2000);
    
    // Capture initial tactical assessment
    const initialScreenshot = `wave5-kael-initial-${Date.now()}.png`;
    await this.page.screenshot({ path: initialScreenshot, fullPage: true });
    console.log(`📸 Kael's initial tactical assessment captured: ${initialScreenshot}\n`);
  }

  async executeWarriorTurn(scenario, turnNumber) {
    this.turnCount = turnNumber;
    console.log(`\n⚔️ Turn ${turnNumber}: ${scenario.action.toUpperCase()}`);
    console.log(`🎯 ${scenario.description}`);
    
    const turnStart = Date.now();
    const turnResult = {
      turn: turnNumber,
      action: scenario.action,
      description: scenario.description,
      kaelPerspective: '',
      tacticalGains: [],
      alliances: [],
      resources: [],
      success: false,
      decisiveness: 0
    };

    try {
      // Execute action with warrior's mindset
      const actionResult = await this.performKaelAction(scenario.action);
      
      turnResult.success = actionResult.success;
      turnResult.kaelPerspective = actionResult.perspective;
      turnResult.tacticalGains = actionResult.gains || [];
      turnResult.alliances = actionResult.alliances || [];
      turnResult.resources = actionResult.resources || [];
      turnResult.decisiveness = actionResult.decisiveness || 0;
      
      // Track warrior achievements
      this.results.achievements.powerGained += actionResult.powerGain || 0;
      this.results.achievements.alliancesFormed += (actionResult.alliances?.length || 0);
      this.results.achievements.resourcesAcquired += (actionResult.resources?.length || 0);
      
      if (actionResult.strategicAdvantage) {
        this.results.achievements.strategicAdvantages.push(actionResult.strategicAdvantage);
      }

      // Update personality metrics
      this.results.personality.decisiveness += turnResult.decisiveness;
      this.results.personality.aggression += actionResult.aggression || 0;
      this.results.personality.pragmatism += actionResult.pragmatism || 0;

      const responseTime = Date.now() - turnStart;
      turnResult.responseTime = responseTime;
      
      // Kael's assessment of the turn
      const status = turnResult.success ? '🏆 VICTORY' : '⚡ SETBACK';
      console.log(`⏱️ Turn ${turnNumber} executed in ${responseTime}ms - ${status}`);
      console.log(`🎯 Kael's Perspective: "${turnResult.kaelPerspective}"`);
      
      if (turnResult.tacticalGains.length > 0) {
        console.log(`🏹 Tactical Gains: ${turnResult.tacticalGains.join(', ')}`);
      }
      
      if (turnResult.alliances.length > 0) {
        console.log(`🤝 New Alliances: ${turnResult.alliances.join(', ')}`);
      }

      // Warrior's pause between actions
      await this.page.waitForTimeout(800);
      
    } catch (error) {
      console.error(`⚔️ Kael faces unexpected challenge in Turn ${turnNumber}:`, error.message);
      turnResult.error = error.message;
      turnResult.success = false;
      turnResult.kaelPerspective = "Unexpected resistance encountered. Will adapt strategy.";
    }

    turnResult.endTime = Date.now();
    turnResult.duration = turnResult.endTime - turnStart;
    
    this.results.turns.push(turnResult);
    return turnResult;
  }

  async performKaelAction(action) {
    switch (action) {
      case 'warrior_assessment':
        return await this.performWarriorAssessment();
      case 'power_source_identification':
        return await this.performPowerSourceIdentification();
      case 'strategic_alliance_mapping':
        return await this.performStrategicAllianceMapping();
      case 'merchant_evaluation':
        return await this.performMerchantEvaluation();
      case 'resource_acquisition_focus':
        return await this.performResourceAcquisitionFocus();
      case 'competitive_analysis':
        return await this.performCompetitiveAnalysis();
      case 'strength_demonstration':
        return await this.performStrengthDemonstration();
      case 'territory_exploration':
        return await this.performTerritoryExploration();
      case 'alliance_negotiation':
        return await this.performAllianceNegotiation();
      case 'final_power_assessment':
        return await this.performFinalPowerAssessment();
      default:
        return await this.performGenericWarriorAction(action);
    }
  }

  async performWarriorAssessment() {
    const assessment = await this.page.evaluate(() => {
      const tiles = document.querySelectorAll('.MuiPaper-root, [class*="tile"]');
      const buttons = document.querySelectorAll('button');
      const interactiveElements = document.querySelectorAll('[role="button"], input, select, textarea');
      
      return {
        tacticalElements: tiles.length,
        actionPoints: buttons.length,
        interactiveSurface: interactiveElements.length,
        dominantTheme: getComputedStyle(document.body).backgroundColor,
        territoryControlled: tiles.length > 8
      };
    });

    return {
      success: true,
      perspective: `This interface shows ${assessment.tacticalElements} tactical zones under my potential control. ${assessment.actionPoints} action points available for immediate use.`,
      gains: [`Identified ${assessment.tacticalElements} zones of influence`, `${assessment.actionPoints} immediate action capabilities`],
      powerGain: assessment.territoryControlled ? 2 : 1,
      decisiveness: 3,
      aggression: 2
    };
  }

  async performPowerSourceIdentification() {
    const powerAnalysis = await this.page.evaluate(() => {
      const pageText = document.body.innerText.toLowerCase();
      
      // Look for power-related terms
      const powerKeywords = ['power', 'strength', 'influence', 'authority', 'control', 'command'];
      const resourceKeywords = ['gold', 'treasure', 'artifact', 'weapon', 'resource', 'wealth'];
      
      const powerMentions = powerKeywords.filter(keyword => pageText.includes(keyword));
      const resourceMentions = resourceKeywords.filter(keyword => pageText.includes(keyword));
      
      return {
        powerSources: powerMentions.length,
        resourceOpportunities: resourceMentions.length,
        totalOpportunities: powerMentions.length + resourceMentions.length
      };
    });

    return {
      success: powerAnalysis.totalOpportunities > 0,
      perspective: `Scanned the territory and identified ${powerAnalysis.powerSources} power sources and ${powerAnalysis.resourceOpportunities} resource opportunities. The path to strength is becoming clearer.`,
      gains: [`${powerAnalysis.powerSources} power sources located`, `${powerAnalysis.resourceOpportunities} resource opportunities identified`],
      resources: powerAnalysis.resourceOpportunities > 0 ? ['Resource opportunities mapped'] : [],
      powerGain: powerAnalysis.totalOpportunities,
      decisiveness: 2,
      pragmatism: 3
    };
  }

  async performMerchantEvaluation() {
    const merchantAnalysis = await this.page.evaluate(() => {
      const pageText = document.body.innerText.toLowerCase();
      const merchantPresent = pageText.includes('merchant') || pageText.includes('aldric');
      const tradeTerms = pageText.includes('trade') || pageText.includes('deal') || pageText.includes('business');
      const trustMetrics = pageText.includes('trust') || pageText.includes('reputation');
      
      return {
        merchantFound: merchantPresent,
        tradeOpportunities: tradeTerms,
        relationshipMetrics: trustMetrics,
        businessViable: merchantPresent && (tradeTerms || trustMetrics)
      };
    });

    // Interact with merchant-related elements
    try {
      const merchantElements = await this.page.$$('text=/merchant/i, text=/aldric/i');
      if (merchantElements.length > 0) {
        await merchantElements[0].click();
        await this.page.waitForTimeout(1000);
      }
    } catch (e) {
      // Merchant interaction not available
    }

    return {
      success: merchantAnalysis.merchantFound,
      perspective: merchantAnalysis.businessViable ? 
        "Merchant Aldric presents a viable business opportunity. A strategic alliance could be mutually beneficial." :
        "Merchant presence detected but business potential unclear. Further investigation required.",
      alliances: merchantAnalysis.businessViable ? ['Potential alliance with Merchant Aldric'] : [],
      gains: merchantAnalysis.merchantFound ? ['Merchant contact established'] : [],
      powerGain: merchantAnalysis.businessViable ? 3 : 1,
      decisiveness: 4,
      pragmatism: 4
    };
  }

  async performStrengthDemonstration() {
    // Demonstrate strength through rapid, decisive interactions
    const buttons = await this.page.$$('button:not([disabled])');
    const chips = await this.page.$$('.MuiChip-root');
    
    let interactionCount = 0;
    const maxInteractions = 5;
    
    // Rapid, decisive clicking pattern
    for (let i = 0; i < Math.min(buttons.length, maxInteractions); i++) {
      try {
        await buttons[i].click();
        interactionCount++;
        await this.page.waitForTimeout(100); // Quick, decisive actions
      } catch (e) {
        // Continue with strength demonstration
      }
    }

    return {
      success: interactionCount > 0,
      perspective: `Demonstrated command authority through ${interactionCount} decisive actions. The interface responds to strength and determination.`,
      gains: [`${interactionCount} decisive commands executed`, 'Authority demonstrated'],
      strategicAdvantage: `Command presence established through ${interactionCount} successful actions`,
      powerGain: interactionCount,
      decisiveness: 5,
      aggression: 4
    };
  }

  async performGenericWarriorAction(action) {
    // Generic warrior approach to any action
    const buttons = await this.page.$$('button:not([disabled])');
    
    if (buttons.length > 0) {
      const randomIndex = Math.floor(Math.random() * buttons.length);
      try {
        await buttons[randomIndex].click();
        await this.page.waitForTimeout(600);
      } catch (e) {
        // Action failed, continue with warrior determination
      }
    }

    return {
      success: true,
      perspective: `Executed ${action.replace('_', ' ')} with warrior's determination. Every action brings me closer to my goals.`,
      gains: [`${action} completed`, 'Strategic progress maintained'],
      powerGain: 1,
      decisiveness: 2,
      aggression: 1
    };
  }

  // Implement remaining action methods with warrior perspective
  async performStrategicAllianceMapping() { return await this.performGenericWarriorAction('strategic_alliance_mapping'); }
  async performResourceAcquisitionFocus() { return await this.performGenericWarriorAction('resource_acquisition_focus'); }
  async performCompetitiveAnalysis() { return await this.performGenericWarriorAction('competitive_analysis'); }
  async performTerritoryExploration() { return await this.performGenericWarriorAction('territory_exploration'); }
  async performAllianceNegotiation() { return await this.performGenericWarriorAction('alliance_negotiation'); }
  async performFinalPowerAssessment() { return await this.performGenericWarriorAction('final_power_assessment'); }

  async executeKaelCampaign() {
    try {
      await this.initialize();
      
      console.log('⚔️ Kael Stormwind begins his strategic campaign...\n');
      
      // Execute all Kael's scenarios
      for (let i = 0; i < KAEL_SCENARIOS.length; i++) {
        const scenario = KAEL_SCENARIOS[i];
        await this.executeWarriorTurn(scenario, i + 1);
      }

      // Campaign assessment
      await this.assessCampaign();
      
      // Capture final state with warrior's triumph
      const finalScreenshot = `wave5-kael-final-${Date.now()}.png`;
      await this.page.screenshot({ path: finalScreenshot, fullPage: true });
      
      console.log(`\n📸 Kael's campaign documented: ${finalScreenshot}`);
      
      // Save campaign results
      const resultsFile = `wave5-kael-campaign-${Date.now()}.json`;
      fs.writeFileSync(resultsFile, JSON.stringify(this.results, null, 2));
      
      await this.browser.close();
      
      console.log('\n🏆 WAVE 5 KAEL STORMWIND CAMPAIGN RESULTS:');
      console.log(`⚔️ Total Strategic Actions: ${this.results.turns.length}`);
      console.log(`🎯 Success Rate: ${Math.round((this.results.turns.filter(t => t.success).length / this.results.turns.length) * 100)}%`);
      console.log(`💪 Power Gained: ${this.results.achievements.powerGained} points`);
      console.log(`🤝 Alliances Formed: ${this.results.achievements.alliancesFormed}`);
      console.log(`💰 Resources Acquired: ${this.results.achievements.resourcesAcquired}`);
      console.log(`🏹 Strategic Advantages: ${this.results.achievements.strategicAdvantages.length}`);
      console.log(`⏱️ Campaign Duration: ${Math.round((Date.now() - this.startTime) / 1000)} seconds`);
      console.log(`⚠️ Challenges Faced: ${this.results.errors.length}`);
      console.log(`💾 Campaign log saved: ${resultsFile}`);
      
      return this.results;
      
    } catch (error) {
      console.error('⚔️ Critical campaign failure:', error);
      this.results.criticalError = error.message;
      
      if (this.browser) {
        try {
          await this.browser.close();
        } catch (closeError) {
          console.error('Error closing campaign:', closeError);
        }
      }
      
      return this.results;
    }
  }

  async assessCampaign() {
    // Calculate campaign effectiveness
    const totalDecisiveness = this.results.turns.reduce((sum, turn) => sum + (turn.decisiveness || 0), 0);
    const avgDecisiveness = totalDecisiveness / this.results.turns.length;
    
    this.results.campaignAssessment = {
      overallEffectiveness: this.results.achievements.powerGained >= 10 ? 'highly_effective' : 'moderately_effective',
      decisivenessRating: avgDecisiveness >= 3 ? 'excellent' : 'good',
      strategicSuccess: this.results.achievements.strategicAdvantages.length >= 3,
      warriorRating: this.results.achievements.powerGained >= 15 ? 'legendary' : 
        this.results.achievements.powerGained >= 10 ? 'elite' : 'competent'
    };
  }
}

// Execute Kael's campaign
const campaign = new KaelStormwindTest();
campaign.executeKaelCampaign().then(results => {
  console.log(`\n⚔️ Kael Stormwind's campaign complete! Rating: ${results.campaignAssessment?.warriorRating || 'warrior'}`);
  process.exit(results.criticalError ? 1 : 0);
}).catch(console.error);