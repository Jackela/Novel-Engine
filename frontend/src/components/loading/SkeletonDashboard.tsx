/**
 * SkeletonDashboard Component (T056)
 * 
 * Loading skeleton for Dashboard component
 * Matches Dashboard layout to prevent CLS during lazy loading
 */

import React from 'react';
import './SkeletonDashboard.css';

export const SkeletonDashboard: React.FC = () => {
  return (
    <div 
      className="skeleton-dashboard"
      role="status"
      aria-busy="true"
      aria-label="Loading dashboard"
      data-testid="skeleton-dashboard"
    >
      {/* Header skeleton */}
      <div className="skeleton-header">
        <div className="skeleton-element skeleton-title" />
        <div className="skeleton-element skeleton-subtitle" />
      </div>

      {/* Stats grid skeleton */}
      <div className="skeleton-stats-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton-stat-card">
            <div className="skeleton-element skeleton-stat-label" />
            <div className="skeleton-element skeleton-stat-value" />
          </div>
        ))}
      </div>

      {/* Main content skeleton */}
      <div className="skeleton-main-content">
        <div className="skeleton-element skeleton-content-block" />
      </div>
    </div>
  );
};

export default SkeletonDashboard;
