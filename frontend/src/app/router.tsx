import { createBrowserRouter, useRouteError } from "react-router-dom";

import { EntryPage } from "@/features/studio/EntryPage";
import { ProjectLibraryPage } from "@/features/studio/ProjectLibraryPage";
import { StudioPage } from "@/features/studio/StudioPage";

function RouteErrorBoundary() {
  const error = useRouteError();
  const message = error instanceof Error ? error.message : null;

  return (
    <div className="entry">
      <div className="entry__panel">
        <h1>Something went wrong</h1>
        <p>
          The application encountered an unexpected error. Please refresh the page to try again.
        </p>
        {message ? <p className="ui-form-error">{message}</p> : null}
      </div>
    </div>
  );
}

const routerFuture = {
  v7_relativeSplatPath: true,
  v7_startTransition: true,
} as const;

export const router = createBrowserRouter(
  [
    { path: "/", element: <EntryPage />, errorElement: <RouteErrorBoundary /> },
    { path: "/projects", element: <ProjectLibraryPage />, errorElement: <RouteErrorBoundary /> },
    {
      path: "/projects/:projectId/:section?",
      element: <StudioPage />,
      errorElement: <RouteErrorBoundary />,
    },
    { path: "*", element: <EntryPage />, errorElement: <RouteErrorBoundary /> },
  ],
  { future: routerFuture },
);
