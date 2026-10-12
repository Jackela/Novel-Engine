import { Loader2 } from "lucide-react";
import { createBrowserRouter, useRouteError } from "react-router-dom";

import { AppCrashFallback } from "@/app/AppCrashFallback";
import { useTranslation } from "@/app/i18n/useTranslation";
import { EntryPage } from "@/features/studio/EntryPage";
import { ProjectLibraryPage } from "@/features/studio/ProjectLibraryPage";

function StudioRouteLoading() {
  const { t } = useTranslation();

  return (
    <main aria-live="polite" className="studio__loading" role="status">
      <Loader2 aria-hidden="true" className="ui-spin" /> {t("shell.status.loading")}
    </main>
  );
}

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
      lazy: async () => ({ Component: (await import("@/features/studio/StudioPage")).StudioPage }),
      HydrateFallback: StudioRouteLoading,
      errorElement: <RouteErrorBoundary />,
    },
    { path: "*", element: <EntryPage />, errorElement: <RouteErrorBoundary /> },
  ],
  { future: routerFuture },
);
