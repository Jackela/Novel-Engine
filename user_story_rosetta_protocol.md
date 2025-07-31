# User Story: Rosetta Protocol Refactoring Epic

## Overview
This epic represents a comprehensive refactoring initiative to establish the "Rosetta Protocol" - a systematic approach to eliminate hardcoded values throughout the Warhammer 40k Multi-Agent Simulator application and implement robust internationalization support.

## User Story

**As a development team**, we want to refactor the entire application to eliminate hardcoded values, **so that** we can support internationalization and maintain constraints consistently across all components.

## Business Value
- **Maintainability**: Centralized constraint and text management reduces code duplication and simplifies updates
- **Internationalization**: Native support for multiple languages enhances user accessibility
- **Consistency**: Unified validation rules prevent conflicts between frontend and backend
- **Quality**: Eliminates the current test failures caused by hardcoded bilingual text mixing

## Acceptance Criteria

### 1. Constraints Centralization ✅
- [ ] Create `src/constraints.json` containing all validation rules:
  - Character name length limits (3-50 characters)
  - Description length limits (10-2000 characters) 
  - Description word count requirements (minimum 3 words)
  - File size limits for uploads
  - Maximum character selection limits
- [ ] Modify all Python backend files to import and use centralized constraints
- [ ] Modify all React frontend components to import and use centralized constraints
- [ ] Remove all hardcoded validation values from codebase

### 2. Frontend Internationalization (i18n) ✅
- [ ] Install and configure i18next library in React application
- [ ] Create `frontend/src/locales/en.json` with all English text content:
  - User interface labels and buttons
  - Error messages and validation text
  - Success messages and notifications
  - Form placeholders and help text
- [ ] Create `frontend/src/locales/zh.json` with all Chinese text content:
  - Complete translation of all English content
  - Proper character encoding and cultural adaptation
- [ ] Replace every hardcoded user-facing string in frontend with i18n function calls
- [ ] Implement language switching capability (optional)

### 3. Backend Internationalization (Enhanced) ✅
- [ ] Create backend i18n system for FastAPI error messages
- [ ] Implement `Accept-Language` header detection
- [ ] Create error message templates in multiple languages
- [ ] Refactor all API error responses to use i18n system

### 4. Code Refactoring ✅
- [ ] **api_server.py**: Replace hardcoded validation with constraints import
- [ ] **persona_agent.py**: Use centralized constraints for character validation
- [ ] **CharacterCreation.jsx**: Implement i18n for all text and use centralized constraints
- [ ] **CharacterSelection.jsx**: Implement i18n for all text content
- [ ] **All test files**: Update to work with new constraint and i18n structure

### 5. Test Compatibility ✅
- [ ] Update `test_api_server.py` to use centralized constraints in assertions
- [ ] Update `CharacterCreation.e2e.spec.js` to expect properly localized error messages
- [ ] Update all Playwright selectors to work with i18n content
- [ ] Ensure 100% test pass rate after refactoring
- [ ] Add new tests for i18n functionality

### 6. Documentation Updates ✅
- [ ] Update README.md with i18n setup and usage instructions
- [ ] Document constraints.json schema and usage
- [ ] Create developer guide for adding new translations
- [ ] Update Architecture_Blueprint.md with i18n architecture details

## Technical Implementation Strategy

### Phase 1: Foundation (Constraints)
1. Analyze all hardcoded values across the codebase
2. Create comprehensive constraints.json schema
3. Implement constraint loading utilities for both frontend and backend

### Phase 2: Frontend i18n Implementation  
1. Install and configure i18next with React
2. Extract all user-facing strings into locale files
3. Implement translation functions throughout components
4. Update component tests for i18n compatibility

### Phase 3: Backend i18n Implementation
1. Create FastAPI i18n middleware
2. Implement Accept-Language header processing
3. Refactor error message generation
4. Update API tests for multilingual responses

### Phase 4: Regression Testing & Quality Assurance
1. Execute complete test suite (pytest + playwright)
2. Identify and resolve any i18n-related test failures
3. Validate constraint consistency across all components
4. Perform end-to-end testing with language switching

## Definition of Done
- ✅ All hardcoded validation constraints eliminated
- ✅ Complete i18n implementation for frontend (English + Chinese)
- ✅ Backend error message i18n system implemented
- ✅ All existing tests updated and passing
- ✅ New i18n-specific tests added and passing
- ✅ Documentation updated to reflect new architecture
- ✅ Zero test failures in complete project test suite

## Risk Mitigation
- **Breaking Changes**: Comprehensive test suite ensures no functionality regression
- **Translation Quality**: Native speaker review for Chinese translations
- **Performance Impact**: Lazy loading of locale files to minimize bundle size
- **Complexity**: Phased implementation approach reduces integration risk

## Success Metrics
- **Code Quality**: Elimination of hardcoded values (Target: 100%)
- **Test Coverage**: Maintain current test coverage while supporting i18n
- **Performance**: No degradation in application performance
- **Maintainability**: Reduced code duplication and improved consistency

---

**Epic Priority**: High
**Estimated Effort**: 3-4 development cycles
**Dependencies**: None (self-contained refactoring)
**Stakeholders**: Development Team, QA Team, Future Internationalization Users

*Generated by Tech-Priest Documenter following the BMAD Method*
*For the glory of the Omnissiah and the sanctity of maintainable code*