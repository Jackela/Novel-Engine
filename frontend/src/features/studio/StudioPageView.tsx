import type { ComponentProps } from "react";

import { StudioEditorPane } from "./StudioEditorPane";
import { StudioInspector } from "./StudioInspector";
import { StudioNavigator } from "./StudioNavigator";
import { StudioStatusbar } from "./StudioStatusbar";
import { StudioTopbar } from "./StudioTopbar";

interface StudioPageViewProps {
  project: ComponentProps<typeof StudioTopbar>["project"];
  onBack: () => void;
  navigator: ComponentProps<typeof StudioNavigator>;
  editor: ComponentProps<typeof StudioEditorPane>;
  inspector: ComponentProps<typeof StudioInspector>;
  statusbar: ComponentProps<typeof StudioStatusbar>;
}

export function StudioPageView({
  project,
  onBack,
  navigator,
  editor,
  inspector,
  statusbar,
}: StudioPageViewProps) {
  return (
    <main className="studio">
      <StudioTopbar project={project} onBack={onBack} />
      <StudioNavigator {...navigator} />
      <StudioEditorPane {...editor} />
      <StudioInspector {...inspector} />
      <StudioStatusbar {...statusbar} />
    </main>
  );
}
