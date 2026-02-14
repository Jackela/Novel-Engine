/**
 * Director Mode feature exports.
 *
 * Director Mode provides tools for narrative pacing analysis, conflict tracking,
 * and story structure visualization. These components help authors optimize
 * the rhythm and flow of their storytelling.
 */

// Components
export { BeatList } from './components/BeatList';
export { BeatSuggestionPopover } from './components/BeatSuggestionPopover';
export { PacingGraph } from './components/PacingGraph';
export { ChapterDashboard } from './components/ChapterDashboard';
export { ChapterBoard } from './components/ChapterBoard';
export { ConflictPanel } from './components/ConflictPanel';
export { PlotlineManager } from './components/PlotlineManager';
export { ForeshadowingPanel } from './components/ForeshadowingPanel';
export { ChapterHealth } from './components/ChapterHealth';
export { CritiqueSidebar } from './components/CritiqueSidebar';

// API Hooks
export {
  useBeats,
  useCreateBeat,
  useUpdateBeat,
  useDeleteBeat,
  useReorderBeats,
} from './api/beatApi';
export { useSuggestBeats, beatSuggestionKeys } from './api/beatSuggestionApi';
export { useChapterPacing, pacingKeys } from './api/pacingApi';
export { useChapterHealth, chapterAnalysisKeys } from './api/chapterAnalysisApi';
export { useScenes, useScene, useUpdateScenePhase, sceneKeys } from './api/sceneApi';
export {
  useConflicts,
  useCreateConflict,
  useUpdateConflict,
  useDeleteConflict,
  conflictKeys,
} from './api/conflictApi';
export {
  usePlotlines,
  usePlotline,
  useScenePlotlines,
  useCreatePlotline,
  useUpdatePlotline,
  useDeletePlotline,
  useLinkSceneToPlotline,
  useUnlinkSceneFromPlotline,
  useSetScenePlotlines,
  plotlineKeys,
} from './api/plotlineApi';
export {
  useForeshadowings,
  useForeshadowing,
  useCreateForeshadowing,
  useUpdateForeshadowing,
  useLinkPayoff,
  useDeleteForeshadowing,
  foreshadowingKeys,
} from './api/foreshadowingApi';
export { useCritiqueScene, critiqueKeys } from './api/critiqueApi';
