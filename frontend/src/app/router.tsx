import { createBrowserRouter, useRouteError } from "react-router-dom";

import { AppCrashFallback } from "@/app/AppCrashFallback";
import { EntryPage } from "@/features/studio/EntryPage";
import { ProjectLibraryPage } from "@/features/studio/ProjectLibraryPage";
import { StudioPage } from "@/features/studio/StudioPage";

function RouteErrorBoundary() {
  const error = useRouteError();
  const message = error instanceof Error ? error.message : null;

  return <AppCrashFallback detail={message} />;
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
