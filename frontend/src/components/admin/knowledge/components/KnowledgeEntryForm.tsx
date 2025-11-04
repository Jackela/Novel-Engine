/**
 * Knowledge Entry Form Component
 * 
 * React component for creating and editing knowledge entries
 * 
 * Features:
 * - Create new knowledge entries
 * - Edit existing knowledge entries
 * - Form validation with error messages
 * - Access control configuration
 * - Loading and error states
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): UI adapter for knowledge management use cases
 * - Article VII (Observability): User action logging and error tracking
 */

import React, { useState, useEffect } from 'react';
import type {
  CreateKnowledgeEntryRequest,
  UpdateKnowledgeEntryRequest} from '../services/knowledgeApi';
import {
  KnowledgeAPI,
  KnowledgeType,
  AccessLevel,
  KnowledgeEntry,
  getKnowledgeTypeLabel,
} from '../services/knowledgeApi';
import type {
  AccessControlConfig,
  AccessControlErrors} from './AccessControlPanel';
import {
  AccessControlPanel
} from './AccessControlPanel';

// ============================================================================
// Types & Interfaces
// ============================================================================

interface KnowledgeEntryFormProps {
  /** Entry ID for edit mode (undefined for create mode) */
  entryId?: string;
  /** Callback when form is successfully submitted */
  onSuccess?: (entryId: string) => void;
  /** Callback when form is canceled */
  onCancel?: () => void;
}

interface FormData {
  content: string;
  knowledge_type: KnowledgeType;
  owning_character_id: string;
  access_control: AccessControlConfig;
}

interface FormErrors {
  content?: string;
  knowledge_type?: string;
  access_control?: AccessControlErrors;
}

// ============================================================================
// Component
// ============================================================================

export const KnowledgeEntryForm: React.FC<KnowledgeEntryFormProps> = ({
  entryId,
  onSuccess,
  onCancel,
}) => {
  const isEditMode = Boolean(entryId);

  // Form state
  const [formData, setFormData] = useState<FormData>({
    content: '',
    knowledge_type: KnowledgeType.WORLD_LORE,
    owning_character_id: '',
    access_control: {
      access_level: AccessLevel.PUBLIC,
      allowed_roles: '',
      allowed_character_ids: '',
    },
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [loading, setLoading] = useState(false);
  const [loadingEntry, setLoadingEntry] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Load existing entry for edit mode
  useEffect(() => {
    if (isEditMode && entryId) {
      loadEntry(entryId);
    }
  }, [entryId, isEditMode]);

  /**
   * Load existing knowledge entry for editing
   */
  const loadEntry = async (id: string) => {
    setLoadingEntry(true);
    try {
      const entry = await KnowledgeAPI.getEntry(id);
      setFormData({
        content: entry.content,
        knowledge_type: entry.knowledge_type,
        owning_character_id: entry.owning_character_id || '',
        access_control: {
          access_level: entry.access_level,
          allowed_roles: entry.allowed_roles.join(', '),
          allowed_character_ids: entry.allowed_character_ids.join(', '),
        },
      });
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Failed to load entry');
    } finally {
      setLoadingEntry(false);
    }
  };

  /**
   * Validate form data
   */
  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};
    const accessControlErrors: AccessControlErrors = {};

    // Content validation
    if (!formData.content.trim()) {
      newErrors.content = 'Content is required';
    }

    // Role-based access validation
    if (
      formData.access_control.access_level === AccessLevel.ROLE_BASED &&
      !formData.access_control.allowed_roles.trim()
    ) {
      accessControlErrors.allowed_roles =
        'At least one role is required for role-based access';
    }

    // Character-specific access validation
    if (
      formData.access_control.access_level === AccessLevel.CHARACTER_SPECIFIC &&
      !formData.access_control.allowed_character_ids.trim()
    ) {
      accessControlErrors.allowed_character_ids =
        'At least one character ID is required for character-specific access';
    }

    // Add access control errors if any exist
    if (Object.keys(accessControlErrors).length > 0) {
      newErrors.access_control = accessControlErrors;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      if (isEditMode && entryId) {
        // Update existing entry
        const updateRequest: UpdateKnowledgeEntryRequest = {
          content: formData.content,
        };
        await KnowledgeAPI.updateEntry(entryId, updateRequest);
        onSuccess?.(entryId);
      } else {
        // Create new entry
        const createRequest: CreateKnowledgeEntryRequest = {
          content: formData.content,
          knowledge_type: formData.knowledge_type,
          owning_character_id: formData.owning_character_id || null,
          access_level: formData.access_control.access_level,
          allowed_roles: formData.access_control.allowed_roles
            ? formData.access_control.allowed_roles.split(',').map((r) => r.trim())
            : [],
          allowed_character_ids: formData.access_control.allowed_character_ids
            ? formData.access_control.allowed_character_ids.split(',').map((id) => id.trim())
            : [],
        };
        const newEntryId = await KnowledgeAPI.createEntry(createRequest);
        onSuccess?.(newEntryId);
      }
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Failed to load entry');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle input change
   */
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error for this field
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  /**
   * Handle access control configuration change
   */
  const handleAccessControlChange = (config: AccessControlConfig) => {
    setFormData((prev) => ({ ...prev, access_control: config }));
    // Clear access control errors
    if (errors.access_control) {
      setErrors((prev) => ({ ...prev, access_control: undefined }));
    }
  };

  // Loading state for edit mode
  if (loadingEntry) {
    return (
      <div className="knowledge-entry-form-loading">
        <p>Loading entry...</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="knowledge-entry-form">
      <h2>{isEditMode ? 'Edit Knowledge Entry' : 'Create Knowledge Entry'}</h2>

      {/* Content */}
      <div className="form-group">
        <label htmlFor="content">
          Content <span className="required">*</span>
        </label>
        <textarea
          id="content"
          name="content"
          value={formData.content}
          onChange={handleChange}
          rows={10}
          placeholder="Enter knowledge content..."
          className={errors.content ? 'error' : ''}
          disabled={loading}
        />
        {errors.content && <span className="error-message">{errors.content}</span>}
      </div>

      {/* Knowledge Type (disabled in edit mode) */}
      <div className="form-group">
        <label htmlFor="knowledge_type">
          Knowledge Type <span className="required">*</span>
        </label>
        <select
          id="knowledge_type"
          name="knowledge_type"
          value={formData.knowledge_type}
          onChange={handleChange}
          disabled={isEditMode || loading}
          className={errors.knowledge_type ? 'error' : ''}
        >
          {Object.values(KnowledgeType).map((type) => (
            <option key={type} value={type}>
              {getKnowledgeTypeLabel(type)}
            </option>
          ))}
        </select>
        {errors.knowledge_type && (
          <span className="error-message">{errors.knowledge_type}</span>
        )}
        {isEditMode && (
          <span className="help-text">Knowledge type cannot be changed after creation</span>
        )}
      </div>

      {/* Owning Character ID (disabled in edit mode) */}
      <div className="form-group">
        <label htmlFor="owning_character_id">Owning Character ID (Optional)</label>
        <input
          type="text"
          id="owning_character_id"
          name="owning_character_id"
          value={formData.owning_character_id}
          onChange={handleChange}
          placeholder="e.g., char-123"
          disabled={isEditMode || loading}
        />
        {isEditMode && (
          <span className="help-text">Owning character cannot be changed after creation</span>
        )}
      </div>

      {/* Access Control Panel */}
      <AccessControlPanel
        value={formData.access_control}
        onChange={handleAccessControlChange}
        errors={errors.access_control}
        disabled={isEditMode || loading}
        showImmutabilityWarning={isEditMode}
      />

      {/* Submit Error */}
      {submitError && (
        <div className="submit-error">
          <strong>Error:</strong> {submitError}
        </div>
      )}

      {/* Actions */}
      <div className="form-actions">
        <button
          type="button"
          onClick={onCancel}
          disabled={loading}
          className="btn btn-secondary"
        >
          Cancel
        </button>
        <button type="submit" disabled={loading} className="btn btn-primary">
          {loading
            ? isEditMode
              ? 'Updating...'
              : 'Creating...'
            : isEditMode
            ? 'Update Entry'
            : 'Create Entry'}
        </button>
      </div>
    </form>
  );
};
