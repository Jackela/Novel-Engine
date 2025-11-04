/**
 * Knowledge Entry List Component
 * 
 * React component for displaying and managing knowledge entries
 * 
 * Features:
 * - List all knowledge entries with filtering
 * - View entry details
 * - Edit existing entries
 * - Delete entries with confirmation
 * - Real-time search and filtering
 * - Pagination support
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): UI adapter for knowledge retrieval
 * - Article VII (Observability): User interaction logging
 */

import React, { useState, useEffect } from 'react';
import type {
  KnowledgeEntry,
  KnowledgeEntryFilters} from '../services/knowledgeApi';
import {
  KnowledgeAPI,
  KnowledgeType,
  getKnowledgeTypeLabel,
  getAccessLevelLabel,
  formatTimestamp,
} from '../services/knowledgeApi';

// ============================================================================
// Types & Interfaces
// ============================================================================

interface KnowledgeEntryListProps {
  /** Callback when user clicks edit button */
  onEdit?: (entryId: string) => void;
  /** Callback after successful deletion */
  onDelete?: (entryId: string) => void;
  /** Callback when user clicks view button */
  onView?: (entryId: string) => void;
  /** Initial filters */
  initialFilters?: KnowledgeEntryFilters;
}

// ============================================================================
// Component
// ============================================================================

export const KnowledgeEntryList: React.FC<KnowledgeEntryListProps> = ({
  onEdit,
  onDelete,
  onView,
  initialFilters,
}) => {
  // State
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [filteredEntries, setFilteredEntries] = useState<KnowledgeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<KnowledgeType | ''>(
    initialFilters?.knowledge_type || ''
  );
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Load entries on mount
  useEffect(() => {
    loadEntries();
  }, []);

  // Apply search and filters when entries or filters change
  useEffect(() => {
    applyFilters();
  }, [entries, searchTerm, filterType]);

  /**
   * Load knowledge entries from API
   */
  const loadEntries = async () => {
    setLoading(true);
    setError(null);

    try {
      const fetchedEntries = await KnowledgeAPI.listEntries(initialFilters);
      setEntries(fetchedEntries);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load entries');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Apply search and type filters
   */
  const applyFilters = () => {
    let result = [...entries];

    // Apply search filter
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (entry) =>
          entry.content.toLowerCase().includes(term) ||
          entry.id.toLowerCase().includes(term) ||
          (entry.owning_character_id && entry.owning_character_id.toLowerCase().includes(term))
      );
    }

    // Apply type filter
    if (filterType) {
      result = result.filter((entry) => entry.knowledge_type === filterType);
    }

    setFilteredEntries(result);
  };

  /**
   * Handle delete confirmation
   */
  const handleDeleteClick = (entryId: string) => {
    setDeleteConfirmId(entryId);
  };

  /**
   * Handle delete confirmation cancel
   */
  const handleDeleteCancel = () => {
    setDeleteConfirmId(null);
  };

  /**
   * Handle delete execution
   */
  const handleDeleteConfirm = async () => {
    if (!deleteConfirmId) return;

    setDeleting(true);
    try {
      await KnowledgeAPI.deleteEntry(deleteConfirmId);
      // Remove from local state
      setEntries((prev) => prev.filter((entry) => entry.id !== deleteConfirmId));
      onDelete?.(deleteConfirmId);
      setDeleteConfirmId(null);
    } catch (err) {
      alert(`Failed to delete entry: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setDeleting(false);
    }
  };

  /**
   * Render loading state
   */
  if (loading) {
    return (
      <div className="knowledge-entry-list-loading">
        <p>Loading knowledge entries...</p>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (error) {
    return (
      <div className="knowledge-entry-list-error">
        <p>
          <strong>Error:</strong> {error}
        </p>
        <button onClick={loadEntries} className="btn btn-primary">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="knowledge-entry-list">
      {/* Header */}
      <div className="list-header">
        <h2>Knowledge Entries ({filteredEntries.length})</h2>
        <button onClick={loadEntries} className="btn btn-secondary btn-sm">
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="list-filters">
        <div className="filter-group">
          <label htmlFor="search">Search:</label>
          <input
            type="text"
            id="search"
            placeholder="Search content, ID, or character..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="filter-input"
          />
        </div>

        <div className="filter-group">
          <label htmlFor="type-filter">Knowledge Type:</label>
          <select
            id="type-filter"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as KnowledgeType | '')}
            className="filter-select"
          >
            <option value="">All Types</option>
            {Object.values(KnowledgeType).map((type) => (
              <option key={type} value={type}>
                {getKnowledgeTypeLabel(type)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Entry List */}
      {filteredEntries.length === 0 ? (
        <div className="list-empty">
          <p>No knowledge entries found.</p>
          {(searchTerm || filterType) && (
            <p>
              <button
                onClick={() => {
                  setSearchTerm('');
                  setFilterType('');
                }}
                className="btn btn-link"
              >
                Clear filters
              </button>
            </p>
          )}
        </div>
      ) : (
        <div className="list-entries">
          {filteredEntries.map((entry) => (
            <div key={entry.id} className="entry-card">
              <div className="entry-header">
                <div className="entry-type-badge">
                  {getKnowledgeTypeLabel(entry.knowledge_type)}
                </div>
                <div className="entry-access-badge">
                  {getAccessLevelLabel(entry.access_level)}
                </div>
              </div>

              <div className="entry-content">
                <p className="entry-text">
                  {entry.content.substring(0, 200)}
                  {entry.content.length > 200 && '...'}
                </p>
              </div>

              <div className="entry-meta">
                <span className="meta-item">
                  <strong>ID:</strong> {entry.id}
                </span>
                {entry.owning_character_id && (
                  <span className="meta-item">
                    <strong>Character:</strong> {entry.owning_character_id}
                  </span>
                )}
                <span className="meta-item">
                  <strong>Created:</strong> {formatTimestamp(entry.created_at)}
                </span>
                <span className="meta-item">
                  <strong>Updated:</strong> {formatTimestamp(entry.updated_at)}
                </span>
              </div>

              <div className="entry-actions">
                {onView && (
                  <button
                    onClick={() => onView(entry.id)}
                    className="btn btn-secondary btn-sm"
                  >
                    View
                  </button>
                )}
                {onEdit && (
                  <button onClick={() => onEdit(entry.id)} className="btn btn-primary btn-sm">
                    Edit
                  </button>
                )}
                <button
                  onClick={() => handleDeleteClick(entry.id)}
                  className="btn btn-danger btn-sm"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Confirm Deletion</h3>
            <p>Are you sure you want to delete this knowledge entry?</p>
            <p>
              <strong>ID:</strong> {deleteConfirmId}
            </p>
            <p className="warning-text">This action cannot be undone.</p>

            <div className="modal-actions">
              <button
                onClick={handleDeleteCancel}
                disabled={deleting}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={deleting}
                className="btn btn-danger"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
