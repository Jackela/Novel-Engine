/**
 * Director Mode feature exports.
 *
 * Director Mode provides tools for narrative pacing analysis, conflict tracking,
 * and story structure visualization. These components help authors optimize
 * the rhythm and flow of their storytelling.
 */

// Components
export { BeatList } from './components/BeatList';
export { PacingGraph } from './components/PacingGraph';
export { ChapterDashboard } from './components/ChapterDashboard';
export { ConflictPanel } from './components/ConflictPanel';

// API Hooks
export { useBeats, useCreateBeat, useUpdateBeat, useDeleteBeat, useReorderBeats } from './api/beatApi';
export { useChapterPacing, pacingKeys } from './api/pacingApi';
export {
  useConflicts,
  useCreateConflict,
  useUpdateConflict,
  useDeleteConflict,
  conflictKeys,
} from './api/conflictApi';
