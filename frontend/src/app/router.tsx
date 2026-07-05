import { createBrowserRouter } from 'react-router-dom';

import { EntryPage } from '@/features/studio/EntryPage';
import { ProjectLibraryPage } from '@/features/studio/ProjectLibraryPage';
import { StudioPage } from '@/features/studio/StudioPage';

const routerFuture = {
  v7_relativeSplatPath: true,
  v7_startTransition: true,
} as const;

export const router = createBrowserRouter(
  [
    { path: '/', element: <EntryPage /> },
    { path: '/projects', element: <ProjectLibraryPage /> },
    { path: '/projects/:projectId/:section?', element: <StudioPage /> },
    { path: '*', element: <EntryPage /> },
  ],
  { future: routerFuture },
);
