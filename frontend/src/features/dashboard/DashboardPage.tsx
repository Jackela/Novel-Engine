/**
 * DashboardPage - Main dashboard orchestrator
 * Thin page component that composes dashboard panels
 */
import { Suspense } from 'react';
import { LoadingSpinner } from '@/shared/components/feedback';
import { DashboardShell } from './components/DashboardShell';

export default function DashboardPage() {
  return (
    <Suspense fallback={<LoadingSpinner fullScreen text="Loading dashboard..." />}>
      <DashboardShell />
    </Suspense>
  );
}
