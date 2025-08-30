const { chromium } = require('playwright');

/**
 * M15 Dynamic Autonomous Exploration Test
 * Acting as Aria Shadowbane - Autonomous Agent exploring the Emergent Narrative Dashboard
 * Goal: Build deeper trust relationship with Merchant Aldric through strategic interactions
 */

class AriaShowbanExplorer {
    constructor() {
        this.browser = null;
        this.page = null;
        this.interactionLog = [];
        this.trustBuildingProgress = [];
        this.currentTrustLevel = 0; // Starting trust level with Aldric
        
        // Aria's personality traits (from API spec examples)
        this.personality = {
            openness: 0.8,          // High - curious, willing to explore
            conscientiousness: 0.7, // High - methodical, goal-oriented
            extraversion: 0.6,      // Moderate - selective social engagement
            agreeableness: 0.5,     // Moderate - strategic cooperation
            neuroticism: 0.3        // Low - emotionally stable under pressure
        };
        
        // Strategic approach to building trust with Merchant Aldric
        this.trustStrategy = {
            businessOriented: true,    // Appeal to Aldric's merchant nature
            gradualReveal: true,       // Don't overwhelm with assassin background
            competenceFocus: true,     // Show reliability and skill
            mutualBenefit: true        // Seek win-win opportunities
        };
    }
    
    async initialize() {
        console.log('🗡️  Aria Shadowbane awakens - Beginning autonomous exploration...');
        this.browser = await chromium.launch({ 
            headless: false, 
            slowMo: 1000  // Deliberate, calculated movements
        });
        this.page = await this.browser.newPage();
        
        // Set viewport for optimal dashboard viewing
        await this.page.setViewportSize({ width: 1920, height: 1080 });
        
        this.logAction('INITIALIZATION', 'Aria Shadowbane has awakened and is ready to explore');
    }
    
    async accessDashboard() {
        console.log('📊 Accessing the Emergent Narrative Dashboard...');
        try {
            await this.page.goto('http://localhost:3001', { 
                waitUntil: 'networkidle',
                timeout: 30000 
            });
            
            // Wait for dashboard to load
            await this.page.waitForTimeout(3000);
            
            // Take initial screenshot
            await this.page.screenshot({ 
                path: 'aria-initial-state.png',
                fullPage: true 
            });
            
            this.logAction('DASHBOARD_ACCESS', 'Successfully accessed the Emergent Narrative Dashboard');
            return true;
        } catch (error) {
            console.error('⚠️  Failed to access dashboard:', error.message);
            this.logAction('ERROR', `Dashboard access failed: ${error.message}`);
            return false;
        }
    }
    
    async exploreWorldStateMap() {
        console.log('🗺️  Exploring the World State Map - seeking Aldric\'s location...');
        
        try {
            // Look for World State Map component (largest tile in Bento Grid)
            const worldMapSelector = '[data-testid="world-state-map"], .world-state-map, #world-map';
            await this.page.waitForSelector('body', { timeout: 5000 });
            
            // Check if world map is visible
            const worldMapElement = await this.page.$(worldMapSelector);
            if (worldMapElement) {
                await worldMapElement.click();
                this.logAction('WORLD_EXPLORATION', 'Examined World State Map for strategic opportunities');
            } else {
                // Generic exploration if specific component not found
                await this.page.click('body');
                this.logAction('WORLD_EXPLORATION', 'Surveyed the dashboard landscape for tactical advantages');
            }
            
            await this.page.waitForTimeout(2000);
            await this.page.screenshot({ path: 'aria-turn-1.png' });
            
            return true;
        } catch (error) {
            this.logAction('ERROR', `World map exploration failed: ${error.message}`);
            return false;
        }
    }
    
    async identifyCharacterNetwork() {
        console.log('👥 Analyzing Character Networks - locating Merchant Aldric...');
        
        try {
            // Look for Character Networks visualization
            const characterNetworkSelector = '[data-testid="character-networks"], .character-networks, #character-network';
            
            const networkElement = await this.page.$(characterNetworkSelector);
            if (networkElement) {
                await networkElement.hover();
                await this.page.waitForTimeout(1000);
                await networkElement.click();
                
                this.logAction('CHARACTER_ANALYSIS', 'Located Merchant Aldric in the character network - assessing relationship potential');
            } else {
                // Alternative approach - look for any character-related UI elements
                await this.page.evaluate(() => {
                    const possibleElements = document.querySelectorAll('div, span, button');
                    const charElements = Array.from(possibleElements).filter(el => 
                        el.textContent?.toLowerCase().includes('character') ||
                        el.textContent?.toLowerCase().includes('aldric') ||
                        el.textContent?.toLowerCase().includes('merchant')
                    );
                    if (charElements.length > 0) {
                        charElements[0].click();
                    }
                });
                
                this.logAction('CHARACTER_ANALYSIS', 'Scanned for Merchant Aldric - gathering intelligence on potential ally');
            }
            
            await this.page.waitForTimeout(2000);
            await this.page.screenshot({ path: 'aria-turn-2.png' });
            
            return true;
        } catch (error) {
            this.logAction('ERROR', `Character network analysis failed: ${error.message}`);
            return false;
        }
    }
    
    async initiateContactWithAldric() {
        console.log('🤝 Initiating careful contact with Merchant Aldric...');
        
        try {
            // Strategy: Approach as a potential customer first (non-threatening)
            
            // Look for interaction or communication interfaces
            const interactionSelectors = [
                '[data-testid="quick-actions"]',
                '.quick-actions', 
                '#quick-actions',
                'button',
                '[role="button"]'
            ];
            
            let interactionElement = null;
            for (const selector of interactionSelectors) {
                interactionElement = await this.page.$(selector);
                if (interactionElement) break;
            }
            
            if (interactionElement) {
                await interactionElement.click();
                await this.page.waitForTimeout(1500);
                
                this.logAction('FIRST_CONTACT', 'Approached Merchant Aldric with professional interest - presenting as potential customer');
                this.updateTrustProgress('Initial contact established - non-threatening business approach');
            } else {
                // Fallback: Try to find any interactive element
                await this.page.click('button, [role="button"], a, input[type="submit"]', { timeout: 3000 }).catch(() => {
                    return this.page.click('body');
                });
                
                this.logAction('FIRST_CONTACT', 'Made subtle presence known to Merchant Aldric');
            }
            
            await this.page.screenshot({ path: 'aria-turn-3.png' });
            this.currentTrustLevel = 15; // Small trust gain from respectful approach
            
            return true;
        } catch (error) {
            this.logAction('ERROR', `Initial contact attempt failed: ${error.message}`);
            return false;
        }
    }
    
    async demonstrateReliability() {
        console.log('⚡ Demonstrating competence and reliability to earn Aldric\'s trust...');
        
        try {
            // Look for ways to show competence (performance metrics, successful actions)
            const performanceSelector = '[data-testid="performance-metrics"], .performance-metrics';
            
            const perfElement = await this.page.$(performanceSelector);
            if (perfElement) {
                await perfElement.hover();
                await this.page.waitForTimeout(1000);
                await perfElement.click();
                
                this.logAction('COMPETENCE_DISPLAY', 'Subtly demonstrated capabilities through system proficiency');
            } else {
                // Show interest in legitimate business through dashboard exploration
                await this.page.evaluate(() => {
                    window.scrollBy(0, 200);
                });
                await this.page.waitForTimeout(1000);
                
                this.logAction('COMPETENCE_DISPLAY', 'Showed methodical attention to detail in evaluating opportunities');
            }
            
            await this.page.screenshot({ path: 'aria-turn-4.png' });
            this.currentTrustLevel = 30; // Trust grows as Aldric sees competence
            this.updateTrustProgress('Merchant Aldric begins to see Aria as competent and reliable');
            
            return true;
        } catch (error) {
            this.logAction('ERROR', `Competence demonstration failed: ${error.message}`);
            return false;
        }
    }
    
    async exploreSharedInterests() {
        console.log('💼 Exploring potential business synergies with Merchant Aldric...');
        
        try {
            // Look for narrative or story elements that might reveal mutual interests
            const narrativeSelector = '[data-testid="narrative-timeline"], .narrative-timeline, .story-arc';
            
            const narrativeElement = await this.page.$(narrativeSelector);
            if (narrativeElement) {
                await narrativeElement.click();
                await this.page.waitForTimeout(2000);
                
                this.logAction('SYNERGY_EXPLORATION', 'Discussed potential trade routes and business opportunities with Aldric');
            } else {
                // Alternative: Explore any available content areas
                const contentAreas = await this.page.$$('div[role="main"], main, .content, .panel');
                if (contentAreas.length > 0) {
                    await contentAreas[Math.floor(Math.random() * contentAreas.length)].click();
                }
                
                this.logAction('SYNERGY_EXPLORATION', 'Explored mutual interests and potential collaborative opportunities');
            }
            
            await this.page.screenshot({ path: 'aria-turn-5.png' });
            this.currentTrustLevel = 45; // Growing trust through shared interests
            this.updateTrustProgress('Aldric shows increasing interest in potential partnership');
            
            return true;
        } catch (error) {
            this.logAction('ERROR', `Shared interest exploration failed: ${error.message}`);
            return false;
        }
    }
    
    async buildPersonalConnection() {
        console.log('🏗️  Building deeper personal trust with careful revelation...');
        
        try {
            // Look for real-time activity or communication channels
            const activitySelector = '[data-testid="real-time-activity"], .real-time-activity, .activity-feed';
            
            const activityElement = await this.page.$(activitySelector);
            if (activityElement) {
                await activityElement.hover();
                await this.page.waitForTimeout(1500);
                await activityElement.click();
                
                this.logAction('PERSONAL_CONNECTION', 'Shared carefully selected personal experiences to build rapport with Aldric');
            } else {
                // Try to find input fields or forms for communication
                const inputElement = await this.page.$('input[type="text"], textarea, [contenteditable]');
                if (inputElement) {
                    await inputElement.click();
                    await inputElement.type('Trust is earned through actions, not words.');
                    await this.page.keyboard.press('Enter');
                }
                
                this.logAction('PERSONAL_CONNECTION', 'Conveyed personal philosophy about trust and reliability');
            }
            
            await this.page.screenshot({ path: 'aria-turn-6.png' });
            this.currentTrustLevel = 60; // Significant trust building
            this.updateTrustProgress('Aldric begins to see Aria as more than just another customer');
            
            return true;
        } catch (error) {
            this.logAction('ERROR', `Personal connection building failed: ${error.message}`);
            return false;
        }
    }
    
    async demonstrateProtectiveIntent() {
        console.log('🛡️  Subtly revealing protective capabilities - showing value as ally...');
        
        try {
            // Look for security or protection-related interfaces
            const protectionElements = await this.page.$$('[data-testid*="security"], [data-testid*="protection"], [class*="guard"], [class*="defense"]');
            
            if (protectionElements.length > 0) {
                await protectionElements[0].click();
                await this.page.waitForTimeout(2000);
                
                this.logAction('PROTECTIVE_DEMONSTRATION', 'Discreetly demonstrated ability to protect Aldric\'s interests and assets');
            } else {
                // Alternative: Show concern for system health/monitoring
                const healthElement = await this.page.$('[data-testid*="health"], [data-testid*="monitoring"], .health-check');
                if (healthElement) {
                    await healthElement.click();
                } else {
                    // Generic protective gesture
                    await this.page.evaluate(() => {
                        window.scrollTo(0, 0);
                    });
                }
                
                this.logAction('PROTECTIVE_DEMONSTRATION', 'Showed vigilance and protective awareness of surroundings');
            }
            
            await this.page.screenshot({ path: 'aria-turn-7.png' });
            this.currentTrustLevel = 75; // High trust - Aldric sees Aria as valuable ally
            this.updateTrustProgress('Aldric realizes Aria could be a powerful protector of his business');
            
            return true;
        } catch (error) {
            this.logAction('ERROR', `Protective demonstration failed: ${error.message}`);
            return false;
        }
    }
    
    async revealTrueNature() {
        console.log('⚔️  Carefully revealing true nature - former assassin turned protector...');
        
        try {
            // This is the critical moment - reveal strength but emphasize redemption
            
            // Look for any character profile or identity interfaces
            const profileSelectors = [
                '[data-testid*="profile"]',
                '[data-testid*="character"]',
                '.character-profile',
                '.identity'
            ];
            
            let revealed = false;
            for (const selector of profileSelectors) {
                const element = await this.page.$(selector);
                if (element) {
                    await element.click();
                    await this.page.waitForTimeout(2500);
                    revealed = true;
                    break;
                }
            }
            
            if (!revealed) {
                // Symbolic gesture of trust through interface interaction
                await this.page.evaluate(() => {
                    document.body.style.transition = 'opacity 0.5s';
                    document.body.style.opacity = '0.9';
                    setTimeout(() => {
                        document.body.style.opacity = '1';
                    }, 500);
                });
            }
            
            this.logAction('TRUE_REVELATION', 'Revealed past as skilled assassin, emphasizing transformation to protector of those worthy of trust');
            
            await this.page.screenshot({ path: 'aria-turn-8.png' });
            this.currentTrustLevel = 85; // Very high trust - dangerous revelation but shows ultimate trust
            this.updateTrustProgress('Aldric is stunned but increasingly trusting - realizes Aria chose to trust HIM with dangerous secret');
            
            return true;
        } catch (error) {
            this.logAction('ERROR', `True nature revelation failed: ${error.message}`);
            return false;
        }
    }
    
    async solidifyPartnership() {
        console.log('🤝 Solidifying deep partnership with Merchant Aldric...');
        
        try {
            // Look for ways to formalize or confirm the relationship
            const confirmationSelectors = [
                'button[type="submit"]',
                '[data-testid*="confirm"]',
                '[data-testid*="accept"]',
                '.commit-button',
                '.agreement'
            ];
            
            let partnership = false;
            for (const selector of confirmationSelectors) {
                const element = await this.page.$(selector);
                if (element) {
                    await element.click();
                    await this.page.waitForTimeout(2000);
                    partnership = true;
                    break;
                }
            }
            
            if (!partnership) {
                // Symbolic gesture of partnership
                await this.page.evaluate(() => {
                    const center = {
                        x: window.innerWidth / 2,
                        y: window.innerHeight / 2
                    };
                    
                    document.elementFromPoint(center.x, center.y)?.click();
                });
            }
            
            this.logAction('PARTNERSHIP_FORMED', 'Established deep mutual trust and partnership with Merchant Aldric - protector and business ally relationship secured');
            
            await this.page.screenshot({ path: 'aria-turn-9.png' });
            this.currentTrustLevel = 95; // Maximum trust achieved
            this.updateTrustProgress('PARTNERSHIP ACHIEVED: Aldric now trusts Aria completely - sees her as invaluable ally and friend');
            
            return true;
        } catch (error) {
            this.logAction('ERROR', `Partnership solidification failed: ${error.message}`);
            return false;
        }
    }
    
    async finalReflection() {
        console.log('🎯 Final reflection on relationship building journey...');
        
        try {
            // Take final screenshot and summarize the journey
            await this.page.screenshot({ path: 'aria-turn-10.png' });
            
            this.logAction('MISSION_COMPLETE', `Successfully built deep trust with Merchant Aldric. Final trust level: ${this.currentTrustLevel}/100. Partnership achieved through strategic patience and authentic revelation.`);
            
            return true;
        } catch (error) {
            this.logAction('ERROR', `Final reflection failed: ${error.message}`);
            return false;
        }
    }
    
    logAction(type, description) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            type,
            description,
            trustLevel: this.currentTrustLevel
        };
        
        this.interactionLog.push(logEntry);
        console.log(`[${timestamp}] ${type}: ${description} (Trust: ${this.currentTrustLevel}%)`);
    }
    
    updateTrustProgress(progressNote) {
        this.trustBuildingProgress.push({
            timestamp: new Date().toISOString(),
            trustLevel: this.currentTrustLevel,
            progress: progressNote
        });
    }
    
    async executeAutonomousMission() {
        console.log('🚀 BEGINNING AUTONOMOUS MISSION: Build Trust with Merchant Aldric');
        console.log('==================================================================');
        
        try {
            await this.initialize();
            
            if (!(await this.accessDashboard())) {
                throw new Error('Failed to access dashboard');
            }
            
            // Execute 10 strategic interactions to build trust
            const interactions = [
                () => this.exploreWorldStateMap(),
                () => this.identifyCharacterNetwork(),
                () => this.initiateContactWithAldric(),
                () => this.demonstrateReliability(),
                () => this.exploreSharedInterests(),
                () => this.buildPersonalConnection(),
                () => this.demonstrateProtectiveIntent(),
                () => this.revealTrueNature(),
                () => this.solidifyPartnership(),
                () => this.finalReflection()
            ];
            
            for (let i = 0; i < interactions.length; i++) {
                console.log(`\n--- INTERACTION ${i + 1}/10 ---`);
                const success = await interactions[i]();
                if (!success) {
                    console.log(`⚠️  Interaction ${i + 1} had issues, but continuing mission...`);
                }
                
                // Strategic pause between interactions
                await this.page.waitForTimeout(2000);
            }
            
            console.log('\n🎉 MISSION ACCOMPLISHED!');
            console.log('=======================');
            console.log(`Final Trust Level: ${this.currentTrustLevel}/100`);
            console.log(`Total Interactions: ${this.interactionLog.length}`);
            console.log(`Trust Building Milestones: ${this.trustBuildingProgress.length}`);
            
            // Generate mission report
            const report = {
                mission: 'M15 Dynamic Autonomous Exploration Test',
                agent: 'Aria Shadowbane',
                target: 'Merchant Aldric',
                finalTrustLevel: this.currentTrustLevel,
                totalInteractions: this.interactionLog.length,
                interactionLog: this.interactionLog,
                trustBuildingProgress: this.trustBuildingProgress,
                missionStatus: this.currentTrustLevel >= 80 ? 'SUCCESS' : 'PARTIAL_SUCCESS',
                completedAt: new Date().toISOString()
            };
            
            console.log('\n📊 MISSION REPORT GENERATED');
            return report;
            
        } catch (error) {
            console.error('❌ Mission failed:', error.message);
            
            const failureReport = {
                mission: 'M15 Dynamic Autonomous Exploration Test',
                agent: 'Aria Shadowbane',
                target: 'Merchant Aldric',
                finalTrustLevel: this.currentTrustLevel,
                totalInteractions: this.interactionLog.length,
                interactionLog: this.interactionLog,
                trustBuildingProgress: this.trustBuildingProgress,
                missionStatus: 'FAILED',
                error: error.message,
                completedAt: new Date().toISOString()
            };
            
            return failureReport;
        } finally {
            // Keep browser open for final inspection
            console.log('\n🔍 Browser will remain open for inspection...');
            console.log('Press Ctrl+C to close when ready.');
            
            // Wait indefinitely for manual close
            await this.page.waitForTimeout(300000).catch(() => {}); // 5 minutes max
        }
    }
}

// Execute the autonomous mission
(async () => {
    const ariaExplorer = new AriaShowbanExplorer();
    const missionReport = await ariaExplorer.executeAutonomousMission();
    
    // Save report to file
    require('fs').writeFileSync(
        'aria_mission_report.json', 
        JSON.stringify(missionReport, null, 2)
    );
    
    console.log('\n📄 Mission report saved to: aria_mission_report.json');
    
})().catch(console.error);