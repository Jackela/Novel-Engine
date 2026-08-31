import { ChevronDown } from "lucide-react";
import { type Dispatch, type SetStateAction, useId } from "react";

import { StudioInspectorPanels } from "./StudioInspectorPanels";
import { StudioInspectorTabs } from "./StudioInspectorTabs";
import type { InspectorTab } from "./studioConstants";
import type { InspectorPendingState, StudioInspectorModel } from "./studioInspectorTypes";

const DEFAULT_INSPECTOR_PENDING: InspectorPendingState = {
  proposal: { running: false, accepting: false },
  review: false,
  jobs: { loading: false, retrying: false },
  settings: false,
};

interface StudioInspectorProps {
  error: string | null;
  inspector: InspectorTab;
  setInspector: Dispatch<SetStateAction<InspectorTab>>;
  pending?: InspectorPendingState;
  /** #412: per-tab model groups assembled once by the page model. */
  model: StudioInspectorModel;
}

export function StudioInspector({
  error,
  inspector,
  setInspector,
  pending = DEFAULT_INSPECTOR_PENDING,
  model,
}: StudioInspectorProps) {
  const inspectorId = useId();
  const tabId = (tab: Exclude<InspectorTab, "settings">) => `${inspectorId}-${tab}-tab`;
  const panelId = (tab: Exclude<InspectorTab, "settings">) => `${inspectorId}-${tab}-panel`;
  const loreError = model.loreStatus?.error ?? null;
  const exportPanelOwnsSharedError =
    inspector === "export" &&
    model.export.errorForExport !== null &&
    model.export.errorForExport === error;
  const sharedError = error !== loreError && !exportPanelOwnsSharedError ? error : null;

  return (
    <aside className="studio-inspector">
      <details className="studio-inspector__disclosure" open>
        <summary className="studio-inspector__summary">
          <span>Inspector</span>
          <ChevronDown aria-hidden="true" />
        </summary>
        <div className="studio-inspector__content">
          {inspector !== "settings" && (
            <StudioInspectorTabs
              inspector={inspector}
              tabId={tabId}
              panelId={panelId}
              setInspector={setInspector}
            />
          )}

          {loreError ? (
            <div aria-live="assertive" className="studio-inspector__error" role="alert">
              {loreError}
            </div>
          ) : null}

          {sharedError ? (
            <div aria-live="assertive" className="studio-inspector__error" role="alert">
              {sharedError}
            </div>
          ) : null}

          <StudioInspectorPanels
            inspector={inspector}
            tabId={tabId}
            panelId={panelId}
            pending={pending}
            model={model}
          />
        </div>
      </details>
    </aside>
  );
}
