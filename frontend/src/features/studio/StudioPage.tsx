import { Loader2 } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { useStudioPageModel } from "./hooks/useStudioPageModel";
import { StudioPageView } from "./StudioPageView";

export function StudioPage() {
  const { projectId = "", section = "manuscript" } = useParams();
  const navigate = useNavigate();
  const { project, viewProps, loadError } = useStudioPageModel(projectId, section, navigate);

  if (!project || !viewProps) {
    // #390: only a missing project navigates away; any other load failure is
    // surfaced as a readable error state instead of a silent redirect.
    if (loadError) {
      return (
        <main className="studio__loading studio-load-error" role="alert">
          <p>{loadError}</p>
        </main>
      );
    }
    return (
      <main className="studio__loading">
        <Loader2 className="ui-spin" /> Loading Studio
      </main>
    );
  }

  return <StudioPageView {...viewProps} />;
}
