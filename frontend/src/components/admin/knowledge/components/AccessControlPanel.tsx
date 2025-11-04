/**
 * Access Control Panel Component
 * 
 * React component for configuring knowledge entry access control rules
 * 
 * Features:
 * - Select access level (PUBLIC, ROLE_BASED, CHARACTER_SPECIFIC)
 * - Configure allowed roles for role-based access
 * - Configure allowed character IDs for character-specific access
 * - Form validation with error messages
 * - Disabled state for edit mode
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): UI adapter for access control configuration
 * - Article V (SOLID): Single Responsibility - access control UI only
 */

import React from 'react';
import { AccessLevel, getAccessLevelLabel } from '../services/knowledgeApi';

// ============================================================================
// Types & Interfaces
// ============================================================================

export interface AccessControlConfig {
  access_level: AccessLevel;
  allowed_roles: string;
  allowed_character_ids: string;
}

export interface AccessControlErrors {
  access_level?: string;
  allowed_roles?: string;
  allowed_character_ids?: string;
}

interface AccessControlPanelProps {
  /** Current access control configuration */
  value: AccessControlConfig;
  /** Callback when configuration changes */
  onChange: (config: AccessControlConfig) => void;
  /** Validation errors for access control fields */
  errors?: AccessControlErrors;
  /** Disable all controls (e.g., in edit mode) */
  disabled?: boolean;
  /** Show help text explaining immutability in edit mode */
  showImmutabilityWarning?: boolean;
}

// ============================================================================
// Component
// ============================================================================

export const AccessControlPanel: React.FC<AccessControlPanelProps> = ({
  value,
  onChange,
  errors = {},
  disabled = false,
  showImmutabilityWarning = false,
}) => {
  /**
   * Handle access level change
   */
  const handleAccessLevelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newAccessLevel = e.target.value as AccessLevel;
    onChange({
      ...value,
      access_level: newAccessLevel,
      // Clear role/character fields when switching access levels
      allowed_roles: newAccessLevel === AccessLevel.ROLE_BASED ? value.allowed_roles : '',
      allowed_character_ids:
        newAccessLevel === AccessLevel.CHARACTER_SPECIFIC ? value.allowed_character_ids : '',
    });
  };

  /**
   * Handle allowed roles change
   */
  const handleRolesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...value,
      allowed_roles: e.target.value,
    });
  };

  /**
   * Handle allowed character IDs change
   */
  const handleCharacterIdsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...value,
      allowed_character_ids: e.target.value,
    });
  };

  return (
    <div className="access-control-panel">
      <h3>Access Control</h3>

      {/* Access Level Selection */}
      <div className="form-group">
        <label htmlFor="access_level">
          Access Level <span className="required">*</span>
        </label>
        <select
          id="access_level"
          name="access_level"
          value={value.access_level}
          onChange={handleAccessLevelChange}
          disabled={disabled}
          className={errors.access_level ? 'error' : ''}
        >
          {Object.values(AccessLevel).map((level) => (
            <option key={level} value={level}>
              {getAccessLevelLabel(level)}
            </option>
          ))}
        </select>
        {errors.access_level && (
          <span className="error-message">{errors.access_level}</span>
        )}
        {showImmutabilityWarning && (
          <span className="help-text">Access level cannot be changed after creation</span>
        )}
      </div>

      {/* Allowed Roles (conditional - only for ROLE_BASED) */}
      {value.access_level === AccessLevel.ROLE_BASED && (
        <div className="form-group">
          <label htmlFor="allowed_roles">
            Allowed Roles <span className="required">*</span>
          </label>
          <input
            type="text"
            id="allowed_roles"
            name="allowed_roles"
            value={value.allowed_roles}
            onChange={handleRolesChange}
            placeholder="e.g., game_master, player"
            disabled={disabled}
            className={errors.allowed_roles ? 'error' : ''}
          />
          <span className="help-text">Comma-separated list of roles</span>
          {errors.allowed_roles && (
            <span className="error-message">{errors.allowed_roles}</span>
          )}
          {showImmutabilityWarning && (
            <span className="help-text">Allowed roles cannot be changed after creation</span>
          )}
        </div>
      )}

      {/* Allowed Character IDs (conditional - only for CHARACTER_SPECIFIC) */}
      {value.access_level === AccessLevel.CHARACTER_SPECIFIC && (
        <div className="form-group">
          <label htmlFor="allowed_character_ids">
            Allowed Character IDs <span className="required">*</span>
          </label>
          <input
            type="text"
            id="allowed_character_ids"
            name="allowed_character_ids"
            value={value.allowed_character_ids}
            onChange={handleCharacterIdsChange}
            placeholder="e.g., char-123, char-456"
            disabled={disabled}
            className={errors.allowed_character_ids ? 'error' : ''}
          />
          <span className="help-text">Comma-separated list of character IDs</span>
          {errors.allowed_character_ids && (
            <span className="error-message">{errors.allowed_character_ids}</span>
          )}
          {showImmutabilityWarning && (
            <span className="help-text">
              Allowed character IDs cannot be changed after creation
            </span>
          )}
        </div>
      )}

      {/* Access Level Descriptions */}
      <div className="access-level-info">
        <h4>Access Level Guide</h4>
        <ul>
          <li>
            <strong>Public:</strong> All agents can access this knowledge entry
          </li>
          <li>
            <strong>Role-Based:</strong> Only agents with specified roles can access
          </li>
          <li>
            <strong>Character-Specific:</strong> Only specified characters can access
          </li>
        </ul>
      </div>
    </div>
  );
};
