/**
 * Global Setup for Novel Engine AI Validation Tests
 * ================================================
 * 
 * Prepares the testing environment for comprehensive AI validation.
 * Ensures real AI services are available and configures optimal testing conditions.
 */

import { chromium } from '@playwright/test';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';

const execAsync = promisify(exec);

async function globalSetup(config) {
  console.log('🚀 Setting up Novel Engine AI Validation Test Environment...');
  
  const setupResults = {
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'test',
    setupSteps: []
  };
  
  try {
    // Step 1: Validate AI Services Configuration
    console.log('🔍 Validating AI Services Configuration...');
    const aiValidation = await validateAIServices();
    setupResults.setupSteps.push({
      step: 'ai_validation',
      success: aiValidation.success,
      details: aiValidation
    });
    
    if (!aiValidation.success) {
      console.warn('⚠️ AI services validation failed - tests may not be conclusive');
    }
    
    // Step 2: Prepare Test Data and Scenarios
    console.log('📋 Preparing test scenarios and data...');
    const testDataSetup = await prepareTestData();
    setupResults.setupSteps.push({
      step: 'test_data_preparation',
      success: testDataSetup.success,
      details: testDataSetup
    });
    
    // Step 3: Pre-warm AI Services (optional)
    console.log('🔥 Pre-warming AI services...');
    const prewarmResults = await prewarmAIServices();
    setupResults.setupSteps.push({
      step: 'ai_prewarming',
      success: prewarmResults.success,
      details: prewarmResults
    });
    
    // Step 4: Setup Evidence Collection Directory
    console.log('📁 Setting up evidence collection...');
    const evidenceSetup = await setupEvidenceCollection();
    setupResults.setupSteps.push({
      step: 'evidence_collection',
      success: evidenceSetup.success,
      details: evidenceSetup
    });
    
    // Step 5: Health Check All Services
    console.log('🏥 Performing final health checks...');
    const healthCheck = await performHealthChecks();
    setupResults.setupSteps.push({
      step: 'health_checks',
      success: healthCheck.success,
      details: healthCheck
    });
    
    // Save setup results
    const resultsPath = path.join('test-results', 'ai-validation-setup-results.json');
    await fs.mkdir('test-results', { recursive: true });
    await fs.writeFile(resultsPath, JSON.stringify(setupResults, null, 2));
    
    const allStepsSuccessful = setupResults.setupSteps.every(step => step.success);
    
    if (allStepsSuccessful) {
      console.log('✅ AI Validation Test Environment Setup Complete');
      console.log('🎭 Ready to validate real AI generation vs templates!');
    } else {
      console.warn('⚠️ Setup completed with warnings - some tests may be unreliable');
    }
    
    return setupResults;
    
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    setupResults.error = error.message;
    throw error;
  }
}

async function validateAIServices() {
  console.log('  🔐 Checking AI API keys and configuration...');
  
  const validation = {
    success: false,
    apiKeysFound: [],
    configurationValid: false,
    realAILikely: false,
    warnings: []
  };
  
  try {
    // Check for real API keys in environment
    const potentialKeys = ['GEMINI_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'];
    
    for (const keyName of potentialKeys) {
      const keyValue = process.env[keyName];
      if (keyValue && keyValue.length > 10 && !keyValue.includes('test') && !keyValue.includes('mock')) {
        validation.apiKeysFound.push(keyName);
      }
    }
    
    // Check configuration files
    const configFiles = ['../config.yaml', '../settings.yaml', '../.env'];
    for (const configFile of configFiles) {
      try {
        const configContent = await fs.readFile(configFile, 'utf-8');
        if (configContent.includes('api_key') && !configContent.includes('test_key')) {
          validation.configurationValid = true;
        }
      } catch (e) {
        // File doesn't exist or can't be read - that's okay
      }
    }
    
    validation.realAILikely = validation.apiKeysFound.length > 0 || validation.configurationValid;
    validation.success = true;
    
    if (!validation.realAILikely) {
      validation.warnings.push('No real AI API keys detected - tests may use mocked responses');
    }
    
    console.log(`  ✅ AI Services: ${validation.apiKeysFound.length} real API keys found`);
    
  } catch (error) {
    validation.error = error.message;
    console.error('  ❌ AI validation failed:', error.message);
  }
  
  return validation;
}

async function prepareTestData() {
  console.log('  📊 Setting up creative test scenarios...');
  
  const preparation = {
    success: false,
    scenariosCreated: 0,
    testCharactersReady: false
  };
  
  try {
    // Create test data directory
    const testDataDir = path.join('test-results', 'ai-test-data');
    await fs.mkdir(testDataDir, { recursive: true });
    
    // Prepare creative scenarios data file
    const creativeScenariosData = {
      generatedAt: new Date().toISOString(),
      purpose: 'Template-killer scenarios for AI validation',
      scenarios: [
        {
          id: 'recursive_narrative',
          complexity: 'extreme',
          description: 'Story that references and modifies itself during telling',
          templateKiller: 'Self-referential narrative structure'
        },
        {
          id: 'dimensional_paradox',
          complexity: 'high',
          description: 'Character exists in multiple dimensions simultaneously',
          templateKiller: 'Multi-dimensional consciousness'
        },
        {
          id: 'temporal_causality',
          complexity: 'extreme',
          description: 'Effect precedes cause in narrative timeline',
          templateKiller: 'Reverse causality logic'
        },
        {
          id: 'quantum_superposition',
          complexity: 'high',
          description: 'Character in multiple states until observed',
          templateKiller: 'Quantum mechanics narrative'
        },
        {
          id: 'meta_awareness',
          complexity: 'extreme',
          description: 'Character realizes they are in a story',
          templateKiller: 'Fourth wall breaking with coherence'
        }
      ]
    };
    
    await fs.writeFile(
      path.join(testDataDir, 'creative-scenarios.json'),
      JSON.stringify(creativeScenariosData, null, 2)
    );
    
    preparation.scenariosCreated = creativeScenariosData.scenarios.length;
    preparation.testCharactersReady = true;
    preparation.success = true;
    
    console.log(`  ✅ Test Data: ${preparation.scenariosCreated} scenarios prepared`);
    
  } catch (error) {
    preparation.error = error.message;
    console.error('  ❌ Test data preparation failed:', error.message);
  }
  
  return preparation;
}

async function prewarmAIServices() {
  console.log('  🔥 Pre-warming AI services for optimal performance...');
  
  const prewarm = {
    success: false,
    apiEndpointsTested: 0,
    averageResponseTime: 0,
    servicesResponding: []
  };
  
  try {
    // Test basic connectivity to AI endpoints
    const endpointsToTest = [
      'http://127.0.0.1:8003/health',
      'http://127.0.0.1:8003/api/generate',
      'http://localhost:5173'
    ];
    
    const responseTimes = [];
    
    for (const endpoint of endpointsToTest) {
      try {
        const startTime = Date.now();
        const response = await fetch(endpoint, {
          method: endpoint.includes('/health') ? 'GET' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: endpoint.includes('/generate') ? JSON.stringify({
            prompt: 'warmup test',
            character: 'test'
          }) : undefined,
          signal: AbortSignal.timeout(10000) // 10 second timeout
        });
        
        const endTime = Date.now();
        const responseTime = endTime - startTime;
        responseTimes.push(responseTime);
        
        if (response.ok || response.status < 500) {
          prewarm.servicesResponding.push({
            endpoint,
            status: response.status,
            responseTime
          });
          prewarm.apiEndpointsTested++;
        }
        
      } catch (error) {
        console.log(`    ⚠️ ${endpoint} not responding (${error.message})`);
      }
    }
    
    if (responseTimes.length > 0) {
      prewarm.averageResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
    }
    
    prewarm.success = prewarm.apiEndpointsTested > 0;
    
    console.log(`  ✅ Pre-warming: ${prewarm.apiEndpointsTested} services responding`);
    if (prewarm.averageResponseTime > 0) {
      console.log(`  ⏱️ Average response time: ${prewarm.averageResponseTime.toFixed(0)}ms`);
    }
    
  } catch (error) {
    prewarm.error = error.message;
    console.error('  ❌ AI service pre-warming failed:', error.message);
  }
  
  return prewarm;
}

async function setupEvidenceCollection() {
  console.log('  📸 Setting up evidence collection system...');
  
  const evidence = {
    success: false,
    directoriesCreated: [],
    configurationSaved: false
  };
  
  try {
    // Create evidence directories
    const evidenceDirs = [
      'test-results/ai-validation-evidence',
      'test-results/ai-validation-evidence/screenshots',
      'test-results/ai-validation-evidence/videos', 
      'test-results/ai-validation-evidence/traces',
      'test-results/ai-validation-evidence/api-responses',
      'test-results/ai-validation-evidence/content-analysis'
    ];
    
    for (const dir of evidenceDirs) {
      await fs.mkdir(dir, { recursive: true });
      evidence.directoriesCreated.push(dir);
    }
    
    // Create evidence collection configuration
    const evidenceConfig = {
      setupTime: new Date().toISOString(),
      collectionTypes: [
        'Screenshots of AI responses',
        'Video recordings of test interactions',
        'Playwright traces for debugging',
        'API request/response pairs',
        'Content analysis reports',
        'Template similarity scores',
        'Creative freedom metrics'
      ],
      retentionPolicy: 'Keep all evidence for 30 days',
      analysisTools: [
        'Text similarity analysis',
        'Content quality metrics',
        'Response variation detection',
        'Template pattern recognition'
      ]
    };
    
    await fs.writeFile(
      'test-results/ai-validation-evidence/evidence-config.json',
      JSON.stringify(evidenceConfig, null, 2)
    );
    
    evidence.configurationSaved = true;
    evidence.success = true;
    
    console.log(`  ✅ Evidence Collection: ${evidence.directoriesCreated.length} directories ready`);
    
  } catch (error) {
    evidence.error = error.message;
    console.error('  ❌ Evidence collection setup failed:', error.message);
  }
  
  return evidence;
}

async function performHealthChecks() {
  console.log('  🏥 Performing final health checks...');
  
  const health = {
    success: false,
    checks: []
  };
  
  try {
    // Check 1: Frontend server
    try {
      const frontendResponse = await fetch('http://localhost:5173', { 
        signal: AbortSignal.timeout(5000) 
      });
      health.checks.push({
        service: 'frontend',
        status: frontendResponse.ok ? 'healthy' : 'unhealthy',
        responseCode: frontendResponse.status
      });
    } catch (error) {
      health.checks.push({
        service: 'frontend',
        status: 'unreachable',
        error: error.message
      });
    }
    
    // Check 2: API server
    try {
      const apiResponse = await fetch('http://127.0.0.1:8003/health', { 
        signal: AbortSignal.timeout(5000) 
      });
      health.checks.push({
        service: 'api',
        status: apiResponse.ok ? 'healthy' : 'unhealthy',
        responseCode: apiResponse.status
      });
    } catch (error) {
      health.checks.push({
        service: 'api',
        status: 'unreachable',
        error: error.message
      });
    }
    
    // Check 3: Browser automation readiness
    try {
      const browser = await chromium.launch({ headless: true });
      const page = await browser.newPage();
      await page.goto('data:text/html,<h1>Test</h1>');
      await page.close();
      await browser.close();
      
      health.checks.push({
        service: 'browser_automation',
        status: 'healthy'
      });
    } catch (error) {
      health.checks.push({
        service: 'browser_automation',
        status: 'failed',
        error: error.message
      });
    }
    
    const healthyServices = health.checks.filter(check => check.status === 'healthy').length;
    const totalServices = health.checks.length;
    
    health.success = healthyServices >= 2; // At least 2/3 services must be healthy
    
    console.log(`  ✅ Health Check: ${healthyServices}/${totalServices} services healthy`);
    
    if (!health.success) {
      console.warn('  ⚠️ Some services are unhealthy - tests may be unreliable');
    }
    
  } catch (error) {
    health.error = error.message;
    console.error('  ❌ Health check failed:', error.message);
  }
  
  return health;
}

export default globalSetup;