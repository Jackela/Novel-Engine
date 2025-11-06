/**
 * SkeletonCard Component (T055)
 * 
 * Loading skeleton that matches CharacterCard layout to prevent CLS
 * Provides visual feedback during data fetch with pulse animation
 * 
 * Accessibility:
 * - aria-busy="true" announces loading state
 * - role="status" for screen reader announcements
 * - Respects prefers-reduced-motion for animations
 * 
 * Performance:
 * - Matches CharacterCard dimensions to prevent Cumulative Layout Shift (CLS)
 * - Target: CLS < 0.1 during skeleton → content transition
 */

import React from 'react';
import './SkeletonCard.css';

interface SkeletonCardProps {
  /** Optional additional CSS class */
  className?: string;
}

export const SkeletonCard: React.FC<SkeletonCardProps> = ({ className = '' }) => {
  return (
    <div
      className={`character-card skeleton-card ${className}`}
      role="status"
      aria-busy="true"
      aria-label="Loading character"
      data-testid="skeleton-card"
    >
      <div className="character-content skeleton-content">
        {/* Skeleton character name */}
        <div className="skeleton-element skeleton-name" />
        
        {/* Skeleton status area */}
        <div className="skeleton-element skeleton-status" />
      </div>
    </div>
  );
};

export default SkeletonCard;
