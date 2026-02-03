/**
 * API Layer Exports
 */
export { api, type ApiError, type ValidationError, type BackendError } from './client';
export { generateCharacter } from './generationApi';
export { generateDialogue } from './dialogueApi';
export { generateScene } from './sceneApi';
export { generateWorld } from './worldApi';

// Narrative Structure API
export {
  listStories,
  getStory,
  createStory,
  updateStory,
  deleteStory,
  listChapters,
  getChapter,
  createChapter,
  updateChapter,
  deleteChapter,
  moveChapter,
  listScenes,
  getScene,
  createScene,
  updateScene,
  deleteScene,
  moveScene,
} from './narrativeApi';

// Social Network Analysis API
export { getSocialAnalysis, getCharacterCentrality } from './socialApi';

// Relationship API
export { generateRelationshipHistory } from './relationshipApi';

// Faction API
export { getFactionDetail } from './factionApi';

// Export API
export {
  getCharacterRelationships,
  buildCharacterExportData,
  downloadAsJson,
  type CharacterExportData,
} from './exportApi';

// Outline Export API (DIR-059)
export {
  generateOutlineMarkdown,
  downloadAsMarkdown,
  exportOutlineAsMarkdown,
  useExportOutline,
  type OutlineExportOptions,
} from './outlineExportApi';
