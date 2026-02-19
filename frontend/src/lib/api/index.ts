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

// Calendar API (SIM-004)
export { useCalendar, useAdvanceCalendar } from './calendarApi';

// Events API (SIM-007)
export {
  useWorldEvents,
  useWorldEvent,
  useCreateEvent,
  getWorldEvents,
  getWorldEvent,
  createWorldEvent,
} from './eventsApi';

// Diplomacy API (SIM-011)
export {
  useDiplomacyMatrix,
  useFactionDiplomacy,
  useSetRelation,
  getDiplomacyMatrix,
  getFactionDiplomacy,
  setRelation,
} from './diplomacyApi';

// Rumors API (SIM-026)
export { useRumors, useRumor, getRumors, getRumor } from './rumorApi';

// Simulation API (SIM-031)
export {
  useSimulationHistory,
  useSimulationTick,
  usePreviewSimulation,
  useCommitSimulation,
  useSnapshots,
  useCreateSnapshot,
  useRestoreSnapshot,
  useDeleteSnapshot,
  previewSimulation,
  commitSimulation,
  getSimulationHistory,
  getSimulationTick,
  createSnapshot,
  listSnapshots,
  restoreSnapshot,
  deleteSnapshot,
} from './simulationApi';
