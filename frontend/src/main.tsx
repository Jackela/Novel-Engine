import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import '@fontsource-variable/geist';

import { router, routerFuture } from '@/app/router';
import '@/index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <RouterProvider future={routerFuture} router={router} />
  </React.StrictMode>,
);
