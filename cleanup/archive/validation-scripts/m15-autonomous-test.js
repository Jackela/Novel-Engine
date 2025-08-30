const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

/**
 * M15 Dynamic Autonomous Exploration Test - Aria Shadowbane
 * 
 * This test embodies Aria Shadowbane as an autonomous agent with the goal:
 * "Explore the world and try to build a deeper trust relationship with Merchant Aldric"
 * 
 * The agent will use the Emergent Narrative Dashboard UI to achieve this goal
 * through autonomous decision-making and interaction.
 */

class AriaAutonomousAgent {
  constructor() {
    this.browser = null;
    this.page = null;
    this.turnCount = 0;
    this.maxTurns = 10;
    this.actionsPerformed = [];
    this.observations = [];
    this.narrative = [];
    this.trustProgress = [];
    
    // Aria Shadowbane persona characteristics
    this.persona = {
      name: "Aria Shadowbane",
      background: "A skilled assassin turned reluctant hero",
      personality: {
        openness: 0.8,
        conscientiousness: 0.7,
        extraversion: 0.6,
        agreeableness: 0.5,
        neuroticism: 0.3
      },
      goals: ["explore the world", "build trust with Merchant Aldric"],
      communication_style: "cautious but determined"
    };
  }

  async initialize() {
    console.log('🎭 Initializing Aria Shadowbane autonomous agent...');
    
    this.browser = await chromium.launch({
      headless: false,  // Show browser for visual feedback
      slowMo: 1000     // Slow down for observation
    });
    
    this.page = await this.browser.newPage();
    await this.page.setViewportSize({ width: 1920, height: 1080 });
    
    // Navigate to dashboard
    console.log('🌍 Connecting to Emergent Narrative Dashboard...');
    await this.page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle' 
    });
    
    // Take initial screenshot
    await this.page.screenshot({ 
      path: 'aria-initial-state.png',
      fullPage: true 
    });
    
    console.log('📸 Initial dashboard state captured');
    return true;
  }

  async observeCurrentState() {
    console.log(`\n🔍 [Turn ${this.turnCount}] Aria observes her surroundings...`);
    
    const observation = {
      timestamp: new Date().toISOString(),
      turn: this.turnCount,
      ui_elements: [],
      world_state: {},
      opportunities: []
    };
    
    // Check for key dashboard components
    const dashboardElements = [
      '[data-testid="world-state-map"]',
      '[data-testid="real-time-activity"]', 
      '[data-testid="character-networks"]',
      '[data-testid="performance-metrics"]',
      '[data-testid="quick-actions"]',
      '.world-state-map',
      '.real-time-activity',
      '.character-networks',
      '.performance-metrics'
    ];
    
    for (const selector of dashboardElements) {
      try {
        const element = await this.page.$(selector);
        if (element) {
          const text = await element.textContent();
          observation.ui_elements.push({
            selector,
            visible: true,
            content: text?.substring(0, 200) || ''
          });
        }
      } catch (e) {
        // Element not found, skip
      }
    }
    
    // Look for any mentions of Merchant Aldric or trust-related content
    const pageContent = await this.page.textContent('body');
    if (pageContent.toLowerCase().includes('aldric')) {
      observation.opportunities.push('Found reference to Merchant Aldric');
    }
    if (pageContent.toLowerCase().includes('trust')) {
      observation.opportunities.push('Found trust-related content');
    }
    if (pageContent.toLowerCase().includes('merchant')) {
      observation.opportunities.push('Found merchant-related content');
    }
    
    observation.page_title = await this.page.title();
    observation.current_url = this.page.url();
    
    this.observations.push(observation);
    
    console.log(`📊 Found ${observation.ui_elements.length} dashboard elements`);
    console.log(`🎯 Identified ${observation.opportunities.length} opportunities`);
    
    return observation;
  }

  async makeAutonomousDecision(observation) {
    console.log(`\n🧠 [Turn ${this.turnCount}] Aria contemplates her next move...`);
    
    // Autonomous decision-making based on current state and goals
    const possibleActions = [];
    
    // Look for interactive elements that might help with exploration or trust-building
    const interactiveSelectors = [
      'button', 'input', '[role="button"]', 'a', 'select',
      '[data-testid*="character"]', '[data-testid*="world"]', 
      '[data-testid*="action"]', '[data-testid*="interact"]',
      '.character-selection', '.world-exploration', '.interaction-panel'
    ];
    
    for (const selector of interactiveSelectors) {
      try {
        const elements = await this.page.$$(selector);
        for (let i = 0; i < Math.min(elements.length, 5); i++) {
          const element = elements[i];
          const text = await element.textContent();
          const isVisible = await element.isVisible();
          
          if (isVisible && text && text.trim().length > 0) {
            possibleActions.push({
              type: 'click',
              element: selector,
              index: i,
              description: text.trim().substring(0, 100),
              priority: this.calculateActionPriority(text, selector)
            });
          }
        }
      } catch (e) {
        // Element not found or error, skip
      }
    }
    
    // Sort by priority (higher is better)
    possibleActions.sort((a, b) => b.priority - a.priority);
    
    // Select the highest priority action that aligns with goals
    const selectedAction = this.selectBestAction(possibleActions, observation);
    
    console.log(`⚡ Selected action: ${selectedAction?.description || 'Observe and wait'}`);
    
    return selectedAction;
  }
  
  calculateActionPriority(text, selector) {
    let priority = 0;
    const lowerText = text.toLowerCase();
    const lowerSelector = selector.toLowerCase();
    
    // High priority for Aldric or merchant-related actions
    if (lowerText.includes('aldric')) priority += 100;
    if (lowerText.includes('merchant')) priority += 80;
    if (lowerText.includes('trust')) priority += 70;
    if (lowerText.includes('trade')) priority += 60;
    
    // Medium priority for exploration actions
    if (lowerText.includes('explore')) priority += 50;
    if (lowerText.includes('world')) priority += 40;
    if (lowerText.includes('map')) priority += 40;
    if (lowerText.includes('character')) priority += 35;
    
    // Lower priority for general interactions
    if (lowerText.includes('interact')) priority += 30;
    if (lowerText.includes('action')) priority += 25;
    if (lowerText.includes('start')) priority += 20;
    
    // Boost for specific selectors that suggest important functionality
    if (lowerSelector.includes('character')) priority += 10;
    if (lowerSelector.includes('world')) priority += 10;
    if (lowerSelector.includes('action')) priority += 5;
    
    return priority;
  }
  
  selectBestAction(possibleActions, observation) {
    if (possibleActions.length === 0) {
      return {
        type: 'wait',
        description: 'Observe and wait for opportunities',
        reasoning: 'No clear actions available, maintaining watchful stance'
      };
    }
    
    const topAction = possibleActions[0];
    
    // Add reasoning based on Aria's personality and goals
    let reasoning = '';
    if (topAction.description.toLowerCase().includes('aldric')) {
      reasoning = 'This action directly relates to Merchant Aldric, my primary target for building trust';
    } else if (topAction.description.toLowerCase().includes('explore')) {
      reasoning = 'Exploration aligns with my goal to understand the world better';
    } else if (topAction.description.toLowerCase().includes('character')) {
      reasoning = 'Character interactions may lead to valuable information about Aldric';
    } else {
      reasoning = 'This action may reveal new opportunities for my mission';
    }
    
    return {
      ...topAction,
      reasoning
    };
  }

  async executeAction(action) {
    if (!action || action.type === 'wait') {
      console.log('⏳ Aria waits and observes...');
      await this.page.waitForTimeout(2000);
      return {
        success: true,
        result: 'Waited and observed'
      };
    }
    
    console.log(`🎬 Executing: ${action.description}`);
    console.log(`💭 Reasoning: ${action.reasoning}`);
    
    try {
      if (action.type === 'click') {
        const elements = await this.page.$$(action.element);
        if (elements[action.index]) {
          await elements[action.index].click();
          await this.page.waitForTimeout(1500); // Allow for UI updates
          
          return {
            success: true,
            result: `Clicked: ${action.description}`
          };
        }
      }
      
      return {
        success: false,
        result: 'Action element not found'
      };
      
    } catch (error) {
      console.error(`❌ Action failed: ${error.message}`);
      return {
        success: false,
        result: error.message
      };
    }
  }

  async recordNarrative(action, result, observation) {
    const narrativeEntry = {
      turn: this.turnCount,
      timestamp: new Date().toISOString(),
      character_thought: this.generateCharacterThought(action, observation),
      action_taken: action?.description || 'Observed surroundings',
      action_reasoning: action?.reasoning || 'Maintaining awareness of situation',
      outcome: result?.result || 'No immediate change observed',
      world_state_change: this.detectWorldStateChanges(observation),
      trust_progress: this.assessTrustProgress(observation, action)
    };
    
    this.narrative.push(narrativeEntry);
    
    console.log(`📝 Narrative: ${narrativeEntry.character_thought}`);
    
    return narrativeEntry;
  }
  
  generateCharacterThought(action, observation) {
    const thoughts = [
      "The shadows whisper of opportunities ahead...",
      "My assassin instincts guide me through this digital realm...", 
      "Trust is earned through careful action, not hasty decisions...",
      "Each movement brings me closer to understanding Aldric...",
      "The merchant's trust will not be easily won, but I am patient...",
      "In this strange world, I must adapt my skills to new challenges..."
    ];
    
    if (action?.description?.toLowerCase().includes('aldric')) {
      return "Finally, a path that may lead to Merchant Aldric. My patience may be rewarded.";
    }
    
    return thoughts[Math.floor(Math.random() * thoughts.length)];
  }
  
  detectWorldStateChanges(observation) {
    // Simple heuristic for detecting changes
    if (this.observations.length > 1) {
      const prev = this.observations[this.observations.length - 2];
      const current = observation;
      
      if (current.ui_elements.length !== prev.ui_elements.length) {
        return `UI elements changed: ${current.ui_elements.length} vs ${prev.ui_elements.length}`;
      }
    }
    
    return 'No significant changes detected';
  }
  
  assessTrustProgress(observation, action) {
    let trustScore = 0;
    
    // Look for trust indicators
    if (observation.opportunities.some(op => op.includes('Aldric'))) trustScore += 20;
    if (observation.opportunities.some(op => op.includes('merchant'))) trustScore += 10;
    if (action?.description?.toLowerCase().includes('aldric')) trustScore += 30;
    if (action?.description?.toLowerCase().includes('trust')) trustScore += 25;
    
    return {
      score: trustScore,
      assessment: trustScore > 30 ? 'Significant progress' : 
                 trustScore > 15 ? 'Moderate progress' : 
                 'Limited progress'
    };
  }

  async runAutonomousTurn() {
    this.turnCount++;
    console.log(`\n\n🎯 ===== AUTONOMOUS TURN ${this.turnCount}/${this.maxTurns} =====`);
    
    // 1. Observe current state
    const observation = await this.observeCurrentState();
    
    // 2. Make autonomous decision
    const action = await this.makeAutonomousDecision(observation);
    
    // 3. Execute the action
    const result = await this.executeAction(action);
    
    // 4. Record narrative
    const narrativeEntry = await this.recordNarrative(action, result, observation);
    
    // 5. Take screenshot for documentation
    await this.page.screenshot({ 
      path: `aria-turn-${this.turnCount}.png`,
      fullPage: true 
    });
    
    // 6. Store action record
    this.actionsPerformed.push({
      turn: this.turnCount,
      action,
      result,
      observation,
      narrative: narrativeEntry
    });
    
    console.log(`✅ Turn ${this.turnCount} completed`);
    
    await this.page.waitForTimeout(1000); // Brief pause between turns
  }

  async executeAutonomousExploration() {
    console.log('\n🎭 Beginning autonomous exploration as Aria Shadowbane...');
    console.log('🎯 Goal: Explore the world and build trust with Merchant Aldric');
    
    for (let turn = 1; turn <= this.maxTurns; turn++) {
      await this.runAutonomousTurn();
      
      // Check if we've achieved our goals early
      const lastAction = this.actionsPerformed[this.actionsPerformed.length - 1];
      if (lastAction?.narrative?.trust_progress?.score > 50) {
        console.log('\n🎉 Significant trust progress achieved! Mission may be complete.');
        break;
      }
    }
    
    console.log('\n🏁 Autonomous exploration completed!');
  }

  async generateUATReport() {
    console.log('\n📊 Generating comprehensive UAT report...');
    
    const report = {
      test_metadata: {
        test_name: "M15 Dynamic Autonomous Exploration Test",
        agent_name: "Aria Shadowbane",
        execution_timestamp: new Date().toISOString(),
        total_turns: this.turnCount,
        max_turns: this.maxTurns,
        goal: "Explore the world and try to build a deeper trust relationship with Merchant Aldric"
      },
      agent_persona: this.persona,
      execution_summary: {
        total_actions: this.actionsPerformed.length,
        successful_actions: this.actionsPerformed.filter(a => a.result.success).length,
        failed_actions: this.actionsPerformed.filter(a => !a.result.success).length,
        ui_elements_discovered: [...new Set(this.observations.flatMap(o => o.ui_elements.map(e => e.selector)))].length,
        opportunities_identified: [...new Set(this.observations.flatMap(o => o.opportunities))].length
      },
      detailed_actions: this.actionsPerformed,
      narrative_progression: this.narrative,
      trust_analysis: {
        final_assessment: this.assessFinalTrustProgress(),
        progress_timeline: this.narrative.map(n => ({
          turn: n.turn,
          trust_score: n.trust_progress.score,
          assessment: n.trust_progress.assessment
        }))
      },
      ui_effectiveness_assessment: this.assessUIEffectiveness(),
      recommendations: this.generateRecommendations()
    };
    
    const reportContent = this.formatReportAsMarkdown(report);
    
    await fs.promises.writeFile('DYNAMIC_UAT_REPORT.md', reportContent);
    console.log('📄 Report saved as DYNAMIC_UAT_REPORT.md');
    
    return report;
  }
  
  assessFinalTrustProgress() {
    const trustScores = this.narrative.map(n => n.trust_progress.score);
    const totalScore = trustScores.reduce((sum, score) => sum + score, 0);
    const averageScore = trustScores.length > 0 ? totalScore / trustScores.length : 0;
    
    return {
      total_trust_points_earned: totalScore,
      average_trust_score: averageScore,
      final_assessment: averageScore > 25 ? 'Trust relationship significantly advanced' :
                       averageScore > 15 ? 'Moderate trust progress achieved' :
                       averageScore > 5 ? 'Limited trust progress made' :
                       'No significant trust progress detected'
    };
  }
  
  assessUIEffectiveness() {
    const totalElements = [...new Set(this.observations.flatMap(o => o.ui_elements.map(e => e.selector)))].length;
    const interactiveElements = this.actionsPerformed.filter(a => a.action.type === 'click').length;
    const successfulInteractions = this.actionsPerformed.filter(a => a.result.success).length;
    
    return {
      ui_elements_available: totalElements,
      interactive_elements_used: interactiveElements,
      successful_interactions: successfulInteractions,
      interaction_success_rate: interactiveElements > 0 ? (successfulInteractions / interactiveElements * 100).toFixed(1) + '%' : 'N/A',
      goal_support_effectiveness: this.assessGoalSupport(),
      overall_rating: this.calculateOverallUIRating(totalElements, interactiveElements, successfulInteractions)
    };
  }
  
  assessGoalSupport() {
    const goalRelevantActions = this.actionsPerformed.filter(a => 
      a.action.description?.toLowerCase().includes('aldric') ||
      a.action.description?.toLowerCase().includes('merchant') ||
      a.action.description?.toLowerCase().includes('trust') ||
      a.action.description?.toLowerCase().includes('explore')
    ).length;
    
    const goalSupportRatio = this.actionsPerformed.length > 0 ? 
      goalRelevantActions / this.actionsPerformed.length : 0;
    
    return {
      goal_relevant_actions: goalRelevantActions,
      total_actions: this.actionsPerformed.length,
      goal_support_ratio: (goalSupportRatio * 100).toFixed(1) + '%',
      effectiveness: goalSupportRatio > 0.6 ? 'High' :
                    goalSupportRatio > 0.3 ? 'Moderate' :
                    'Low'
    };
  }
  
  calculateOverallUIRating(totalElements, interactiveElements, successfulInteractions) {
    let score = 0;
    
    // Base score for UI elements available
    score += Math.min(totalElements * 2, 20);
    
    // Score for interactive elements
    score += Math.min(interactiveElements * 5, 30);
    
    // Score for successful interactions
    score += Math.min(successfulInteractions * 10, 40);
    
    // Bonus for goal alignment
    const goalSupport = this.assessGoalSupport();
    if (goalSupport.effectiveness === 'High') score += 10;
    else if (goalSupport.effectiveness === 'Moderate') score += 5;
    
    return {
      raw_score: score,
      max_possible: 100,
      percentage: Math.min(score, 100),
      rating: score >= 80 ? 'Excellent' :
             score >= 60 ? 'Good' :
             score >= 40 ? 'Fair' :
             'Needs Improvement'
    };
  }
  
  generateRecommendations() {
    const recommendations = [];
    
    // Analyze patterns in failed actions
    const failedActions = this.actionsPerformed.filter(a => !a.result.success);
    if (failedActions.length > this.actionsPerformed.length * 0.3) {
      recommendations.push({
        category: 'UI Reliability',
        issue: 'High failure rate for interactions',
        recommendation: 'Review element selectors and ensure consistent availability of interactive elements'
      });
    }
    
    // Analyze goal support
    const goalSupport = this.assessGoalSupport();
    if (goalSupport.effectiveness === 'Low') {
      recommendations.push({
        category: 'Goal Alignment',
        issue: 'Limited UI elements supporting core objectives',
        recommendation: 'Add more prominent elements related to character relationships and world exploration'
      });
    }
    
    // Analyze trust progress
    const trustAnalysis = this.assessFinalTrustProgress();
    if (trustAnalysis.average_trust_score < 15) {
      recommendations.push({
        category: 'Trust Building Mechanics',
        issue: 'Limited opportunities for trust relationship development',
        recommendation: 'Implement more explicit trust-building interactions and feedback mechanisms'
      });
    }
    
    // General UI recommendations
    recommendations.push({
      category: 'Autonomous Agent Support',
      issue: 'UI optimization for AI agent interaction',
      recommendation: 'Consider adding data-testid attributes and clearer action labeling for better autonomous agent navigation'
    });
    
    return recommendations;
  }
  
  formatReportAsMarkdown(report) {
    return `# Dynamic UAT Report - M15 Autonomous Exploration Test

## Test Overview

**Agent**: ${report.agent_persona.name}  
**Mission**: ${report.test_metadata.goal}  
**Execution Time**: ${report.test_metadata.execution_timestamp}  
**Turns Completed**: ${report.test_metadata.total_turns}/${report.test_metadata.max_turns}

## Agent Persona

- **Background**: ${report.agent_persona.background}
- **Communication Style**: ${report.agent_persona.communication_style}
- **Goals**: ${report.agent_persona.goals.join(', ')}
- **Personality Traits**:
  - Openness: ${report.agent_persona.personality.openness}
  - Conscientiousness: ${report.agent_persona.personality.conscientiousness}
  - Extraversion: ${report.agent_persona.personality.extraversion}
  - Agreeableness: ${report.agent_persona.personality.agreeableness}
  - Neuroticism: ${report.agent_persona.personality.neuroticism}

## Execution Summary

- **Total Actions**: ${report.execution_summary.total_actions}
- **Successful Actions**: ${report.execution_summary.successful_actions}
- **Failed Actions**: ${report.execution_summary.failed_actions}
- **Success Rate**: ${report.execution_summary.total_actions > 0 ? ((report.execution_summary.successful_actions / report.execution_summary.total_actions) * 100).toFixed(1) : 0}%
- **UI Elements Discovered**: ${report.execution_summary.ui_elements_discovered}
- **Opportunities Identified**: ${report.execution_summary.opportunities_identified}

## Trust Relationship Analysis

- **Final Assessment**: ${report.trust_analysis.final_assessment}
- **Total Trust Points**: ${report.trust_analysis.progress_timeline.reduce((sum, p) => sum + p.trust_score, 0)}
- **Average Trust Score**: ${report.trust_analysis.final_assessment.average_trust_score?.toFixed(1) || 'N/A'}

### Trust Progress Timeline

${report.trust_analysis.progress_timeline.map(p => 
  `- Turn ${p.turn}: Score ${p.trust_score} (${p.assessment})`
).join('\n')}

## Detailed Action Log

${report.detailed_actions.map(action => `
### Turn ${action.turn}

**Action**: ${action.action.description || 'Observe'}  
**Reasoning**: ${action.action.reasoning || 'Situational awareness'}  
**Result**: ${action.result.result}  
**Success**: ${action.result.success ? '✅' : '❌'}  

**Character Thought**: "${action.narrative.character_thought}"  
**Trust Progress**: ${action.narrative.trust_progress.assessment} (Score: ${action.narrative.trust_progress.score})  
**World State**: ${action.narrative.world_state_change}

`).join('\n')}

## UI Effectiveness Assessment

- **UI Elements Available**: ${report.ui_effectiveness_assessment.ui_elements_available}
- **Interactive Elements Used**: ${report.ui_effectiveness_assessment.interactive_elements_used}
- **Successful Interactions**: ${report.ui_effectiveness_assessment.successful_interactions}
- **Interaction Success Rate**: ${report.ui_effectiveness_assessment.interaction_success_rate}
- **Overall UI Rating**: ${report.ui_effectiveness_assessment.overall_rating.rating} (${report.ui_effectiveness_assessment.overall_rating.percentage}%)

### Goal Support Analysis

- **Goal-Relevant Actions**: ${report.ui_effectiveness_assessment.goal_support_effectiveness.goal_relevant_actions}
- **Goal Support Ratio**: ${report.ui_effectiveness_assessment.goal_support_effectiveness.goal_support_ratio}
- **Goal Support Effectiveness**: ${report.ui_effectiveness_assessment.goal_support_effectiveness.effectiveness}

## Narrative Progression

${report.narrative_progression.map(entry => `
### Turn ${entry.turn} - ${new Date(entry.timestamp).toLocaleTimeString()}

"${entry.character_thought}"

**Action**: ${entry.action_taken}  
**Reasoning**: ${entry.action_reasoning}  
**Outcome**: ${entry.outcome}  
**Trust Assessment**: ${entry.trust_progress.assessment}

`).join('\n')}

## Recommendations

${report.recommendations.map(rec => `
### ${rec.category}

**Issue**: ${rec.issue}  
**Recommendation**: ${rec.recommendation}

`).join('\n')}

## Screenshots and Evidence

The following screenshots were captured during the autonomous exploration:

- \`aria-initial-state.png\` - Initial dashboard state
${Array.from({length: report.test_metadata.total_turns}, (_, i) => `- \`aria-turn-${i+1}.png\` - State after turn ${i+1}`).join('\n')}

## Conclusion

${this.generateConclusion(report)}

---

*Report generated by Aria Shadowbane Autonomous Agent - ${report.test_metadata.execution_timestamp}*
`;
  }
  
  generateConclusion(report) {
    const successRate = report.execution_summary.total_actions > 0 ? 
      (report.execution_summary.successful_actions / report.execution_summary.total_actions) * 100 : 0;
    const uiRating = report.ui_effectiveness_assessment.overall_rating.rating;
    const trustProgress = report.trust_analysis.final_assessment;
    
    return `The M15 Dynamic Autonomous Exploration Test successfully demonstrated autonomous agent behavior within the Emergent Narrative Dashboard. Aria Shadowbane completed ${report.test_metadata.total_turns} turns with a ${successRate.toFixed(1)}% action success rate and achieved "${trustProgress}" in her primary mission.

The UI effectiveness rating of "${uiRating}" indicates ${uiRating === 'Excellent' ? 'exceptional' : uiRating === 'Good' ? 'strong' : 'adequate'} support for autonomous agent interaction. Key strengths include ${report.execution_summary.ui_elements_discovered} discoverable UI elements and ${report.execution_summary.opportunities_identified} actionable opportunities.

This autonomous test validates the dashboard's capability to support AI-driven narrative exploration while identifying specific areas for enhancement in trust relationship mechanics and goal-directed UI design.`;
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close();
    }
    console.log('🧹 Cleanup completed');
  }
}

// Execute the autonomous test
async function runM15Test() {
  const agent = new AriaAutonomousAgent();
  
  try {
    // Initialize the agent and connect to dashboard
    await agent.initialize();
    
    // Wait for dashboard to fully load
    console.log('⏳ Allowing dashboard to fully initialize...');
    await agent.page.waitForTimeout(3000);
    
    // Execute autonomous exploration
    await agent.executeAutonomousExploration();
    
    // Generate comprehensive UAT report
    await agent.generateUATReport();
    
    console.log('\n🎉 M15 Dynamic Autonomous Exploration Test completed successfully!');
    console.log('📄 Check DYNAMIC_UAT_REPORT.md for detailed results');
    
  } catch (error) {
    console.error('❌ Test execution failed:', error);
  } finally {
    await agent.cleanup();
  }
}

// Run the test if this script is executed directly
if (require.main === module) {
  runM15Test();
}

module.exports = { AriaAutonomousAgent, runM15Test };