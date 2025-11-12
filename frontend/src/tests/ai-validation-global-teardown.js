/**
 * Global Teardown for Novel Engine AI Validation Tests
 * ===================================================
 * 
 * Cleans up after AI validation tests, processes evidence, and generates
 * final analysis reports on AI generation validation results.
 */

import fs from 'fs/promises';
import path from 'path';

async function globalTeardown(config) {
  console.log('🧹 Starting AI Validation Test Environment Cleanup...');
  
  const teardownResults = {
    timestamp: new Date().toISOString(),
    teardownSteps: []
  };
  
  try {
    // Step 1: Process and analyze collected evidence
    console.log('📊 Processing collected evidence...');
    const evidenceAnalysis = await processCollectedEvidence();
    teardownResults.teardownSteps.push({
      step: 'evidence_processing',
      success: evidenceAnalysis.success,
      details: evidenceAnalysis
    });
    
    // Step 2: Generate AI validation summary report
    console.log('📋 Generating AI validation summary...');
    const summaryReport = await generateValidationSummary();
    teardownResults.teardownSteps.push({
      step: 'summary_report',
      success: summaryReport.success,
      details: summaryReport
    });
    
    // Step 3: Archive test artifacts
    console.log('📦 Archiving test artifacts...');
    const archiveResults = await archiveTestArtifacts();
    teardownResults.teardownSteps.push({
      step: 'artifact_archival',
      success: archiveResults.success,
      details: archiveResults
    });
    
    // Step 4: Generate final assessment
    console.log('🏆 Generating final AI validation assessment...');
    const finalAssessment = await generateFinalAssessment();
    teardownResults.teardownSteps.push({
      step: 'final_assessment',
      success: finalAssessment.success,
      details: finalAssessment
    });
    
    // Save teardown results
    const resultsPath = path.join('test-results', 'ai-validation-teardown-results.json');
    await fs.writeFile(resultsPath, JSON.stringify(teardownResults, null, 2));
    
    console.log('✅ AI Validation Test Environment Cleanup Complete');
    
    // Print final assessment to console
    if (finalAssessment.success && finalAssessment.assessment) {
      printFinalAssessment(finalAssessment.assessment);
    }
    
    return teardownResults;
    
  } catch (error) {
    console.error('❌ Global teardown failed:', error);
    teardownResults.error = error.message;
    throw error;
  }
}

async function processCollectedEvidence() {
  console.log('  🔍 Analyzing collected test evidence...');
  
  const analysis = {
    success: false,
    evidenceFiles: [],
    screenshots: 0,
    videos: 0,
    traces: 0,
    apiResponses: 0,
    analysisResults: {}
  };
  
  try {
    const evidenceDir = 'test-results/ai-validation-evidence';
    
    // Check if evidence directory exists
    try {
      await fs.access(evidenceDir);
    } catch (error) {
      console.log('  ⚠️ No evidence directory found - tests may not have run');
      analysis.success = true; // Not an error, just no evidence
      return analysis;
    }
    
    // Process different types of evidence
    const subdirs = ['screenshots', 'videos', 'traces', 'api-responses'];
    
    for (const subdir of subdirs) {
      const subdirPath = path.join(evidenceDir, subdir);
      
      try {
        const files = await fs.readdir(subdirPath);
        analysis[subdir.replace('-', '').toLowerCase()] = files.length;
        
        for (const file of files) {
          const filePath = path.join(subdirPath, file);
          const stats = await fs.stat(filePath);
          analysis.evidenceFiles.push({
            type: subdir,
            filename: file,
            size: stats.size,
            created: stats.birthtime.toISOString()
          });
        }
      } catch (error) {
        // Directory might not exist - that's okay
      }
    }
    
    // Generate evidence summary
    analysis.analysisResults = {
      totalEvidenceFiles: analysis.evidenceFiles.length,
      evidenceTypes: {
        visual: analysis.screenshots + analysis.videos,
        technical: analysis.traces + analysis.apiresponses,
        total: analysis.evidenceFiles.length
      },
      evidenceQuality: analysis.evidenceFiles.length > 0 ? 'good' : 'limited'
    };
    
    analysis.success = true;
    
    console.log(`  ✅ Evidence Processing: ${analysis.evidenceFiles.length} files analyzed`);
    
  } catch (error) {
    analysis.error = error.message;
    console.error('  ❌ Evidence processing failed:', error.message);
  }
  
  return analysis;
}

async function generateValidationSummary() {
  console.log('  📈 Generating AI validation summary report...');
  
  const summary = {
    success: false,
    reportGenerated: false,
    testResults: null,
    aiValidationScore: 0
  };
  
  try {
    // Try to read Playwright test results
    const resultFiles = [
      'test-results/ai-validation-results.json',
      'test-results/results.json',
      'test-results/test-results.json'
    ];
    
    let testData = null;
    
    for (const resultFile of resultFiles) {
      try {
        const content = await fs.readFile(resultFile, 'utf-8');
        testData = JSON.parse(content);
        break;
      } catch (error) {
        // Try next file
      }
    }
    
    if (testData) {
      // Process test results for AI validation insights
      summary.testResults = {
        totalTests: 0,
        passedTests: 0,
        failedTests: 0,
        aiValidationTests: 0,
        templateDetectionTests: 0,
        creativityTests: 0
      };
      
      // Extract test statistics (structure may vary by Playwright version)
      if (testData.suites) {
        for (const suite of testData.suites) {
          for (const spec of suite.specs || []) {
            for (const test of spec.tests || []) {
              summary.testResults.totalTests++;
              
              if (test.outcome === 'passed') {
                summary.testResults.passedTests++;
              } else if (test.outcome === 'failed') {
                summary.testResults.failedTests++;
              }
              
              // Categorize AI validation specific tests
              const title = test.title || '';
              if (title.includes('AI Generation') || title.includes('Creative')) {
                summary.testResults.aiValidationTests++;
              }
              if (title.includes('Template') || title.includes('Pattern')) {
                summary.testResults.templateDetectionTests++;
              }
              if (title.includes('Creativity') || title.includes('Freedom')) {
                summary.testResults.creativityTests++;
              }
            }
          }
        }
      }
      
      // Calculate AI validation score
      const passRate = summary.testResults.totalTests > 0 
        ? (summary.testResults.passedTests / summary.testResults.totalTests) 
        : 0;
      
      summary.aiValidationScore = Math.round(passRate * 100);
    }
    
    // Generate summary report
    const validationSummary = {
      generatedAt: new Date().toISOString(),
      testSuite: 'Novel Engine AI Generation Validation',
      purpose: 'Validate real AI generation vs templates/state machines',
      results: summary.testResults,
      aiValidationScore: summary.aiValidationScore,
      assessment: determineAIAssessment(summary.aiValidationScore, summary.testResults),
      recommendations: generateRecommendations(summary.testResults, summary.aiValidationScore)
    };
    
    // Save summary report
    const summaryPath = path.join('test-results', 'ai-validation-summary.json');
    await fs.writeFile(summaryPath, JSON.stringify(validationSummary, null, 2));
    
    summary.reportGenerated = true;
    summary.success = true;
    
    console.log(`  ✅ Summary Report: AI validation score ${summary.aiValidationScore}%`);
    
  } catch (error) {
    summary.error = error.message;
    console.error('  ❌ Summary generation failed:', error.message);
  }
  
  return summary;
}

async function archiveTestArtifacts() {
  console.log('  📦 Archiving test artifacts for long-term storage...');
  
  const archive = {
    success: false,
    artifactsArchived: 0,
    archiveSize: 0
  };
  
  try {
    // Create archive directory with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const archiveDir = path.join('test-results', 'archives', `ai-validation-${timestamp}`);
    await fs.mkdir(archiveDir, { recursive: true });
    
    // List of directories/files to archive
    const itemsToArchive = [
      'test-results/ai-validation-evidence',
      'test-results/ai-validation-artifacts',
      'test-results/ai-validation-results.json',
      'test-results/ai-validation-summary.json',
      'test-results/ai-validation-setup-results.json',
      'test-results/ai-validation-teardown-results.json'
    ];
    
    for (const item of itemsToArchive) {
      try {
        const stats = await fs.stat(item);
        
        if (stats.isDirectory()) {
          // Copy directory recursively
          await copyDirectory(item, path.join(archiveDir, path.basename(item)));
        } else {
          // Copy individual file
          await fs.copyFile(item, path.join(archiveDir, path.basename(item)));
        }
        
        archive.artifactsArchived++;
        archive.archiveSize += stats.size;
        
      } catch (error) {
        // Item might not exist - that's okay
        console.log(`    ⚠️ Could not archive ${item}: ${error.message}`);
      }
    }
    
    // Create archive manifest
    const manifest = {
      createdAt: new Date().toISOString(),
      testSuite: 'Novel Engine AI Validation',
      artifactsCount: archive.artifactsArchived,
      totalSize: archive.archiveSize,
      retentionPolicy: 'Keep for 90 days for compliance and analysis',
      contents: itemsToArchive
    };
    
    await fs.writeFile(
      path.join(archiveDir, 'archive-manifest.json'),
      JSON.stringify(manifest, null, 2)
    );
    
    archive.success = true;
    
    console.log(`  ✅ Archive: ${archive.artifactsArchived} items archived`);
    
  } catch (error) {
    archive.error = error.message;
    console.error('  ❌ Archiving failed:', error.message);
  }
  
  return archive;
}

async function generateFinalAssessment() {
  console.log('  🎯 Generating final AI validation assessment...');
  
  const assessment = {
    success: false,
    assessment: null
  };
  
  try {
    // Read summary report if available
    let summaryData = null;
    
    try {
      const summaryContent = await fs.readFile('test-results/ai-validation-summary.json', 'utf-8');
      summaryData = JSON.parse(summaryContent);
    } catch (error) {
      // Summary might not exist - that's okay, we'll do basic assessment
    }
    
    // Read setup results
    let setupData = null;
    
    try {
      const setupContent = await fs.readFile('test-results/ai-validation-setup-results.json', 'utf-8');
      setupData = JSON.parse(setupContent);
    } catch (error) {
      // Setup data might not exist
    }
    
    // Generate final assessment
    const finalAssessment = {
      timestamp: new Date().toISOString(),
      testSuite: 'Novel Engine AI Generation Validation',
      overallResult: 'INCONCLUSIVE',
      confidence: 'LOW',
      aiValidationScore: summaryData?.aiValidationScore || 0,
      keyFindings: [],
      recommendations: [],
      technicalDetails: {
        environmentSetup: setupData ? 'COMPLETED' : 'INCOMPLETE',
        testExecution: summaryData ? 'COMPLETED' : 'INCOMPLETE',
        evidenceCollection: 'COMPLETED'
      }
    };
    
    // Determine overall result based on available data
    if (summaryData?.aiValidationScore >= 80) {
      finalAssessment.overallResult = 'REAL_AI_VALIDATED';
      finalAssessment.confidence = 'HIGH';
      finalAssessment.keyFindings.push('High confidence that Novel Engine uses real AI generation');
      finalAssessment.keyFindings.push('Tests passed with strong evidence of creative AI responses');
      finalAssessment.keyFindings.push('Template patterns were not detected in generated content');
    } else if (summaryData?.aiValidationScore >= 60) {
      finalAssessment.overallResult = 'LIKELY_REAL_AI';
      finalAssessment.confidence = 'MEDIUM';
      finalAssessment.keyFindings.push('Evidence suggests real AI usage but with some concerns');
      finalAssessment.keyFindings.push('Some tests passed indicating AI generation capabilities');
    } else if (summaryData?.aiValidationScore >= 40) {
      finalAssessment.overallResult = 'MIXED_RESULTS';
      finalAssessment.confidence = 'LOW';
      finalAssessment.keyFindings.push('Results are inconclusive about real AI vs templates');
      finalAssessment.keyFindings.push('Both AI-like and template-like patterns detected');
    } else if (summaryData?.aiValidationScore > 0) {
      finalAssessment.overallResult = 'LIKELY_TEMPLATES';
      finalAssessment.confidence = 'MEDIUM';
      finalAssessment.keyFindings.push('Evidence suggests template-based responses');
      finalAssessment.keyFindings.push('Limited creativity and variation detected');
    } else {
      finalAssessment.overallResult = 'INCONCLUSIVE';
      finalAssessment.confidence = 'LOW';
      finalAssessment.keyFindings.push('Insufficient data to make determination');
    }
    
    // Add environment-based findings
    if (setupData?.setupSteps) {
      const aiValidationStep = setupData.setupSteps.find(step => step.step === 'ai_validation');
      if (aiValidationStep && !aiValidationStep.details?.realAILikely) {
        finalAssessment.keyFindings.push('No real AI API keys detected during setup');
        finalAssessment.recommendations.push('Configure real AI API keys for conclusive testing');
      }
    }
    
    // Add recommendations based on results
    if (finalAssessment.overallResult === 'REAL_AI_VALIDATED') {
      finalAssessment.recommendations.push('Continue monitoring AI generation quality');
      finalAssessment.recommendations.push('Consider implementing additional creativity metrics');
    } else {
      finalAssessment.recommendations.push('Review AI integration implementation');
      finalAssessment.recommendations.push('Ensure real AI services are properly configured');
      finalAssessment.recommendations.push('Run tests with known good AI configuration');
    }
    
    // Save final assessment
    const assessmentPath = path.join('test-results', 'final-ai-validation-assessment.json');
    await fs.writeFile(assessmentPath, JSON.stringify(finalAssessment, null, 2));
    
    assessment.assessment = finalAssessment;
    assessment.success = true;
    
    console.log(`  ✅ Final Assessment: ${finalAssessment.overallResult} (${finalAssessment.confidence} confidence)`);
    
  } catch (error) {
    assessment.error = error.message;
    console.error('  ❌ Final assessment failed:', error.message);
  }
  
  return assessment;
}

function printFinalAssessment(assessment) {
  console.log('\n' + '='.repeat(80));
  console.log('🏆 NOVEL ENGINE AI VALIDATION - FINAL ASSESSMENT');
  console.log('='.repeat(80));
  
  console.log(`📅 Assessment Date: ${new Date(assessment.timestamp).toLocaleString()}`);
  console.log(`🎯 Overall Result: ${assessment.overallResult}`);
  console.log(`📊 Confidence Level: ${assessment.confidence}`);
  console.log(`💯 AI Validation Score: ${assessment.aiValidationScore}%`);
  console.log('');
  
  console.log('🔍 KEY FINDINGS:');
  assessment.keyFindings.forEach(finding => {
    console.log(`   • ${finding}`);
  });
  console.log('');
  
  console.log('💡 RECOMMENDATIONS:');
  assessment.recommendations.forEach(recommendation => {
    console.log(`   • ${recommendation}`);
  });
  console.log('');
  
  // Interpretation guide
  console.log('📋 RESULT INTERPRETATION:');
  switch (assessment.overallResult) {
    case 'REAL_AI_VALIDATED':
      console.log('   ✅ Novel Engine is using REAL AI generation successfully');
      console.log('   ✅ Creative scenarios handled well, template patterns absent');
      break;
    case 'LIKELY_REAL_AI':
      console.log('   ✅ Evidence suggests real AI usage with minor concerns');
      console.log('   ⚠️ Some areas may need optimization or configuration');
      break;
    case 'MIXED_RESULTS':
      console.log('   ⚠️ Results are inconclusive - further investigation needed');
      console.log('   ⚠️ May be using mix of AI and template responses');
      break;
    case 'LIKELY_TEMPLATES':
      console.log('   ❌ Evidence suggests template-based responses dominate');
      console.log('   ❌ Real AI integration may not be working properly');
      break;
    default:
      console.log('   ❓ Insufficient data to make conclusive determination');
      console.log('   ❓ Check test environment and configuration');
  }
  
  console.log('='.repeat(80));
}

// Helper functions
function determineAIAssessment(score, results) {
  if (score >= 80) return 'EXCELLENT_AI_GENERATION';
  if (score >= 60) return 'GOOD_AI_GENERATION';
  if (score >= 40) return 'MODERATE_AI_GENERATION';
  if (score >= 20) return 'POOR_AI_GENERATION';
  return 'NO_AI_DETECTED';
}

function generateRecommendations(results, score) {
  const recommendations = [];
  
  if (score < 70) {
    recommendations.push('Review AI model configuration and API key setup');
    recommendations.push('Verify that real AI services are being called, not mocks');
  }
  
  if (results?.templateDetectionTests > 0) {
    recommendations.push('Investigate template pattern detection results');
  }
  
  if (results?.creativityTests === 0) {
    recommendations.push('Run additional creativity validation tests');
  }
  
  recommendations.push('Monitor AI generation quality in production');
  recommendations.push('Implement continuous AI validation in CI/CD pipeline');
  
  return recommendations;
}

async function copyDirectory(src, dest) {
  await fs.mkdir(dest, { recursive: true });
  
  const entries = await fs.readdir(src, { withFileTypes: true });
  
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    
    if (entry.isDirectory()) {
      await copyDirectory(srcPath, destPath);
    } else {
      await fs.copyFile(srcPath, destPath);
    }
  }
}

export default globalTeardown;