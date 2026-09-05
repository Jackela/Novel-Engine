import { Loader2 } from "lucide-react";
import { useRef } from "react";
import { Navigate, useLocation, useNavigate, useParams } from "react-router-dom";
import { useCommandFocusRestoration } from "./hooks/useCommandFocusRestoration";
import { useStudioPageModel } from "./hooks/useStudioPageModel";
import { StudioPageView } from "./StudioPageView";
import { resolveStudioRoute, type StudioRouteState } from "./studioRouteState";

interface StudioProjectPageProps {
  readonly projectId: string;
  readonly route: StudioRouteState;
}

function StudioProjectPage({ projectId, route }: StudioProjectPageProps) {
  const navigate = useNavigate();
  const { project, viewProps, loadError, isLoading, retryLoad } = useStudioPageModel(
    projectId,
    route,
    navigate,
  );
  const studioHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const runRetryWithFocusRestoration = useCommandFocusRestoration(isLoading);

  if (!project || !viewProps) {
    if (loadError) {
      return (
        <main
          aria-labelledby="studio-load-error-heading"
          className="studio__loading studio-load-error"
        >
          <div aria-live="assertive" role="alert">
            <h1 id="studio-load-error-heading">Unable to open this project</h1>
            <p>{loadError}</p>
          </div>
          <div className="studio-load-error__actions">
            <button
              aria-busy={isLoading || undefined}
              className="ui-command ui-command--primary"
              disabled={isLoading}
              onClick={(event) => {
                void runRetryWithFocusRestoration(
                  event.currentTarget,
                  retryLoad,
                  () => studioHeadingRef.current,
                );
              }}
              type="button"
            >
              {isLoading ? <Loader2 aria-hidden="true" className="ui-spin" /> : null}
              Try again
            </button>
            <button className="ui-command" onClick={() => navigate("/projects")} type="button">
              Back to projects
            </button>
          </div>
        </main>
      );
    }
    return (
      <main aria-live="polite" className="studio__loading" role="status">
        <Loader2 aria-hidden="true" className="ui-spin" /> Loading Studio
      </main>
    );
  }

  return <StudioPageView {...viewProps} headingRef={studioHeadingRef} />;
}

export function StudioPage() {
  const { projectId = "", section } = useParams();
  const location = useLocation();
  const route = resolveStudioRoute(projectId, section, location.search);
  const currentPath = `${location.pathname}${location.search}`;

  if (currentPath !== route.canonicalPath) {
    return <Navigate replace to={route.canonicalPath} />;
  }

  // The route project identity owns every local hook below this boundary.
  // Switching projects unmounts the complete workbench before old state can
  // remain interactive while the next aggregate loads.
  return <StudioProjectPage key={projectId} projectId={projectId} route={route} />;
}
