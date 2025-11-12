# Emergent Narrative Dashboard - User Acceptance Testing (UAT)

## Overview

This document provides comprehensive instructions for executing the AI-driven User Acceptance Test (UAT) suite for the Emergent Narrative Dashboard. The UAT validates the core user story: triggering turn orchestration and observing real-time updates across the Bento Grid components.

## 📋 Prerequisites

### System Requirements
- Node.js 18.x or higher
- npm 9.x or higher
- Chrome, Firefox, or Safari browsers installed
- Network access to API endpoints

### Installation
```bash
# Install dependencies
npm install

# Install Playwright browsers
npm run playwright:install

# Install system dependencies (Linux/macOS)
npm run playwright:install-deps
```

## 🧪 UAT Test Suite

### Core User Story
The UAT validates this primary user journey:

1. **Application Start** - Dashboard loads with all components visible
2. **Turn Orchestration Trigger** - User clicks play button to start turn orchestration  
3. **Real-time Updates** - Components update across the Bento Grid:
   - World State Map shows activity indicators
   - Real-time Activity displays new events
   - Performance Metrics show system health
   - Character Networks reflect relationship changes
   - Narrative Timeline updates progress markers
4. **Specification Compliance** - UI changes match design specifications
5. **API Contract Validation** - Network requests follow OpenAPI contract

### Test Components

#### 🎯 Core UAT Test (`dashboard-core-uat.spec.ts`)
- **Primary user story validation**
- **6-phase test execution**:
  1. Application State Validation
  2. Turn Orchestration Trigger
  3. Pipeline Monitoring (5 phases)
  4. Component Updates Observation
  5. UI Specification Compliance
  6. API Contract Validation
- **Performance benchmarking**
- **Error handling validation**

#### 🖥️ Cross-Browser Testing
- Chrome (Chromium)
- Firefox
- Safari (WebKit)
- Consistent behavior validation

#### 📱 Responsive Design Testing
- Desktop (1440x900)
- Tablet (1024x768)
- Mobile (375x667)
- Layout adaptation validation

#### ⚡ Performance Validation
- Dashboard load time (<5s)
- Component render time
- Turn orchestration response time
- Memory usage monitoring

## 🚀 Running UAT Tests

### Quick Start
```bash
# Run complete UAT suite
npm run test:uat

# Run UAT in CI mode (non-interactive)
npm run test:uat:ci

# Run individual Playwright test
npm run test:e2e tests/e2e/dashboard-core-uat.spec.ts

# Run with browser UI (for debugging)
npm run test:e2e:headed
```

### Manual Test Execution
```bash
# 1. Start the development server
npm run dev

# 2. In another terminal, run UAT
npm run test:uat

# 3. View results
open ./test-results/uat-reports/uat-report.html
```

### Test Configuration

#### Environment Variables
```bash
# Dashboard URL (default: http://localhost:3000)
PLAYWRIGHT_BASE_URL=http://localhost:3000

# API endpoints
TEST_API_URL=http://localhost:8000/v1
TEST_WS_URL=ws://localhost:8001/ws

# Test data
UAT_TEST_CHARACTERS='[{"id":"char-001","name":"Aria Shadowbane",...}]'
UAT_TEST_ARCS='[{"id":"arc-001","name":"The Ancient Prophecy",...}]'
UAT_TEST_CAMPAIGN='{"id":"campaign-001","name":"Test Campaign",...}'
```

#### Browser Selection
```bash
# Run on specific browser
npx playwright test --project=chromium-desktop
npx playwright test --project=firefox-desktop
npx playwright test --project=webkit-desktop

# Run on mobile/tablet
npx playwright test --project=tablet
npx playwright test --project=mobile
```

## 📊 UAT Reports

### Report Generation
The UAT suite automatically generates comprehensive reports:

- **HTML Report**: `./test-results/uat-reports/uat-report.html`
  - Executive summary with pass/fail metrics
  - Detailed test phase breakdown
  - Visual evidence (screenshots)
  - Performance metrics analysis
  - Validation results by category
  - Actionable recommendations

- **JSON Report**: `./test-results/uat-reports/uat-report.json`
  - Machine-readable test results
  - Programmatic access to metrics
  - Integration with CI/CD pipelines

- **Performance Report**: `./test-results/uat-reports/performance-report.json`
  - Load time measurements
  - Component render performance
  - Memory usage tracking
  - Comparative benchmarks

### Report Structure

#### Executive Summary
- Total tests executed
- Pass/fail breakdown with percentages
- Overall test duration
- System health status

#### Test Environment
- Browser and version
- Viewport dimensions
- Test execution timestamp
- Base URL and API endpoints

#### Validation Results
- **Component Validation**: UI element visibility and behavior
- **Layout Validation**: CSS Grid positioning and responsiveness  
- **Performance Validation**: Load times and interaction response
- **API Validation**: Network request compliance with OpenAPI spec
- **Accessibility Validation**: WCAG compliance and keyboard navigation

#### Visual Evidence
- Screenshots at key test phases
- Before/after comparisons
- Error state captures
- Cross-browser visual differences

## 🔍 Debugging UAT Tests

### Common Issues

#### Dashboard Not Loading
```bash
# Check if dashboard is accessible
curl -f http://localhost:3000

# Start development server
npm run dev

# Check port availability
lsof -i :3000
```

#### Test Timeouts
```bash
# Increase timeout for complex operations
PLAYWRIGHT_TIMEOUT=120000 npm run test:uat

# Run in headed mode to observe
npm run test:e2e:headed
```

#### Component Selectors Not Found
- Verify `data-testid` attributes are present
- Check component naming consistency
- Review responsive layout changes

#### Network Request Failures
```bash
# Check API server status
curl -f http://localhost:8000/v1/health

# Verify WebSocket connection
curl -f http://localhost:8001/ws
```

### Debug Mode
```bash
# Run with debug output
DEBUG=pw:* npm run test:uat

# Slow motion for visual debugging
npx playwright test --slow-mo=1000

# Record trace for analysis
npx playwright test --trace=on
```

## 📈 Performance Benchmarks

### Expected Performance Thresholds

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Dashboard Load Time | <3s | 3-5s | >5s |
| Component Render Time | <1s | 1-2s | >2s |
| Turn Orchestration Response | <500ms | 500ms-1s | >1s |
| Layout Reflow Time | <100ms | 100-200ms | >200ms |
| Memory Usage | <100MB | 100-200MB | >200MB |

### Performance Optimization
- Enable browser caching
- Optimize component re-renders
- Implement code splitting
- Use lazy loading for large components
- Monitor WebSocket connection efficiency

## 🔧 Test Maintenance

### Updating Test Data
```typescript
// Modify test-results/TestDataHelpers.ts
const testCharacters = TestDataGenerator.generateTestCharacters(10);
```

### Adding New Validations
```typescript
// In DashboardPage.ts
async validateNewFeature() {
  const newComponent = this.page.locator('[data-testid="new-feature"]');
  await expect(newComponent).toBeVisible();
  return true;
}
```

### Extending UAT Coverage
1. Add new test phases to `dashboard-core-uat.spec.ts`
2. Update validation criteria in `TestDataHelpers.ts`
3. Extend reporting metrics in `UATReporter.ts`

## 🎯 Success Criteria

### Test Completion Requirements
- ✅ All core user story phases pass
- ✅ Cross-browser compatibility validated  
- ✅ Responsive behavior confirmed
- ✅ Performance thresholds met
- ✅ API contract compliance verified
- ✅ Accessibility standards maintained
- ✅ Zero critical errors or exceptions

### UAT Acceptance Criteria
- **Primary User Story**: 100% phase completion
- **Component Updates**: All Bento Grid components show real-time changes
- **Layout Integrity**: CSS Grid positioning maintained across viewports
- **Performance**: Load time <5s, interaction response <1s
- **Reliability**: Tests pass consistently across 3 browser engines

## 🤝 Contributing

### Adding New Tests
1. Create test file in `tests/e2e/`
2. Extend `DashboardPage` with new interactions
3. Add validation methods to `TestDataHelpers`
4. Update UAT runner to include new test

### Reporting Issues
Include in bug reports:
- UAT report HTML file
- Screenshot/video evidence
- Browser and system information
- Console logs and network traces

---

**Generated by**: Emergent Narrative Dashboard UAT Suite  
**Last Updated**: Wave 3 Implementation  
**Contact**: Development Team