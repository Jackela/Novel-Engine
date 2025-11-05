/**
 * Knowledge Management Page
 * 
 * Main page for Game Masters to manage knowledge entries
 * 
 * Features:
 * - Create new knowledge entries
 * - View existing knowledge entries
 * - Edit knowledge entry content
 * - Delete knowledge entries
 * - Search and filter entries
 * - Modal-based create/edit interface
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): UI adapter orchestrating knowledge management components
 * - Article VII (Observability): User interaction tracking and error reporting
 * 
 * User Story 1 Requirement:
 * - Enable Game Masters to create, update, and delete knowledge entries through Admin Web UI
 * - Replacing manual Markdown file editing with database-backed CRUD operations
 */

import React, { useState } from 'react';
import { logger } from '../../../../services/logging/LoggerFactory';
import { KnowledgeEntryList } from '../components/KnowledgeEntryList';
import { KnowledgeEntryForm } from '../components/KnowledgeEntryForm';

// ============================================================================
// Types & Interfaces
// ============================================================================

type ViewMode = 'list' | 'create' | 'edit' | 'view';

interface ViewState {
  mode: ViewMode;
  selectedEntryId?: string;
}

// ============================================================================
// Component
// ============================================================================

export const KnowledgeManagementPage: React.FC = () => {
  // View state
  const [viewState, setViewState] = useState<ViewState>({
    mode: 'list',
  });

  // Navigation handlers
  const handleCreate = () => {
    setViewState({ mode: 'create' });
  };

  const handleEdit = (entryId: string) => {
    setViewState({ mode: 'edit', selectedEntryId: entryId });
  };

  const handleView = (entryId: string) => {
    setViewState({ mode: 'view', selectedEntryId: entryId });
  };

  const handleBackToList = () => {
    setViewState({ mode: 'list' });
  };

  // Success handlers
  const handleCreateSuccess = (entryId: string) => {
    logger.info('[KnowledgeManagementPage] Entry created successfully:', entryId);
    setViewState({ mode: 'list' });
    // Show success notification (TODO: integrate with notification system)
    alert(`Knowledge entry created successfully!\nID: ${entryId}`);
  };

  const handleUpdateSuccess = (entryId: string) => {
    logger.info('[KnowledgeManagementPage] Entry updated successfully:', entryId);
    setViewState({ mode: 'list' });
    // Show success notification (TODO: integrate with notification system)
    alert(`Knowledge entry updated successfully!\nID: ${entryId}`);
  };

  const handleDeleteSuccess = (entryId: string) => {
    logger.info('[KnowledgeManagementPage] Entry deleted successfully:', entryId);
    // Show success notification (TODO: integrate with notification system)
    alert(`Knowledge entry deleted successfully!\nID: ${entryId}`);
  };

  // Render based on view mode
  return (
    <div className="knowledge-management-page">
      {/* Page Header */}
      <header className="page-header">
        <h1>Knowledge Management</h1>
        <p className="page-description">
          Manage centralized knowledge entries for agents and game sessions.
          Create, update, and organize world lore, character backgrounds, faction information, and
          more.
        </p>
      </header>

      {/* Main Content */}
      <main className="page-content">
        {viewState.mode === 'list' && (
          <>
            {/* Action Bar */}
            <div className="action-bar">
              <button onClick={handleCreate} className="btn btn-primary">
                + Create New Entry
              </button>
            </div>

            {/* Knowledge Entry List */}
            <KnowledgeEntryList
              onEdit={handleEdit}
              onDelete={handleDeleteSuccess}
              onView={handleView}
            />
          </>
        )}

        {viewState.mode === 'create' && (
          <div className="form-container">
            <KnowledgeEntryForm onSuccess={handleCreateSuccess} onCancel={handleBackToList} />
          </div>
        )}

        {viewState.mode === 'edit' && viewState.selectedEntryId && (
          <div className="form-container">
            <KnowledgeEntryForm
              entryId={viewState.selectedEntryId}
              onSuccess={handleUpdateSuccess}
              onCancel={handleBackToList}
            />
          </div>
        )}

        {viewState.mode === 'view' && viewState.selectedEntryId && (
          <div className="view-container">
            <div className="view-header">
              <h2>View Knowledge Entry</h2>
              <button onClick={handleBackToList} className="btn btn-secondary">
                Back to List
              </button>
            </div>
            {/* TODO: Implement read-only view component */}
            <p>Entry ID: {viewState.selectedEntryId}</p>
            <p>
              <em>Detailed view coming soon...</em>
            </p>
          </div>
        )}
      </main>

      {/* Page Footer */}
      <footer className="page-footer">
        <p className="help-text">
          <strong>Getting Started:</strong> Click "Create New Entry" to add knowledge to the
          centralized database. Knowledge entries are automatically available to agents based on
          access control rules.
        </p>
        <p className="help-text">
          <strong>Migration:</strong> To migrate existing Markdown files, use the Migration Tool
          (coming soon).
        </p>
      </footer>
    </div>
  );
};

// Export default for React Router integration
export default KnowledgeManagementPage;
