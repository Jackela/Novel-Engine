import { AlertCircle, Check, Loader2 } from 'lucide-react';

import type { SaveState, StudioDocument } from '@/app/types/studio';

interface StudioStatusbarProps {
  activeDocument: StudioDocument | null;
  loadedRevisionId: string | null;
  saveState: SaveState;
}

export function StudioStatusbar({
  activeDocument,
  loadedRevisionId,
  saveState,
}: StudioStatusbarProps) {
  return (
    <footer className="studio-statusbar">
      <span>
        {saveState === 'error' ? (
          <AlertCircle />
        ) : saveState === 'saving' ? (
          <Loader2 className="spin" />
        ) : (
          <Check />
        )}{' '}
        {saveState === 'saving'
          ? 'Saving'
          : saveState === 'conflict'
            ? 'Conflict'
            : saveState === 'error'
              ? 'Error'
              : 'Saved'}
      </span>
      <span>Revision {loadedRevisionId?.slice(0, 8) ?? 'none'}</span>
      <span className="studio-statusbar__spacer" />
      <span>{activeDocument?.word_count ?? 0} words</span>
      <span>Novel Studio {__APP_VERSION__}</span>
    </footer>
  );
}
