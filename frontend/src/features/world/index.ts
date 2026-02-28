/**
 * World feature module exports
 */
export { default as WorldPage } from './WorldPage';

// API hooks
export {
  useFactionIntents,
  useGenerateIntents,
  useSelectIntent,
  useFactionIntel,
  factionIntelKeys,
} from './api/factionIntelApi';

// Components
export { FactionIntelPanel } from './components/FactionIntelPanel';
export type { FactionIntelPanelProps } from './components/FactionIntelPanel';
