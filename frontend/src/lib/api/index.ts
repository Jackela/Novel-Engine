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
