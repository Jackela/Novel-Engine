/**
 * Knowledge Management Module
 * 
 * Exports all knowledge management components and services
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): UI adapter module for knowledge management
 */

// Components
export { KnowledgeEntryForm } from './components/KnowledgeEntryForm';
export { KnowledgeEntryList } from './components/KnowledgeEntryList';

// Pages
export { KnowledgeManagementPage } from './pages/KnowledgeManagementPage';
export { default as KnowledgeManagementPageDefault } from './pages/KnowledgeManagementPage';

// Services
export {
  KnowledgeAPI,
  KnowledgeType,
  AccessLevel,
  formatTimestamp,
  getKnowledgeTypeLabel,
  getAccessLevelLabel,
} from './services/knowledgeApi';

export type {
  KnowledgeEntry,
  CreateKnowledgeEntryRequest,
  UpdateKnowledgeEntryRequest,
  KnowledgeEntryFilters,
} from './services/knowledgeApi';
