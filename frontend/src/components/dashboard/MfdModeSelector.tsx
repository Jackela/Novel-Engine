import React from 'react';
import { ToggleButton, ToggleButtonGroup, styled } from '@mui/material';

/**
 * MFD (Multi-Function Display) mode options
 */
export type MfdMode = 'analytics' | 'network' | 'timeline' | 'signals';

interface MfdModeOption {
  id: MfdMode;
  label: string;
  description?: string;
}

/**
 * Default MFD mode configuration
 */
export const MFD_MODES: readonly MfdModeOption[] = [
  { id: 'analytics', label: 'DATA', description: 'Analytics Dashboard' },
  { id: 'network', label: 'NET', description: 'Character Networks' },
  { id: 'timeline', label: 'TIME', description: 'Narrative Timeline' },
  { id: 'signals', label: 'SIG', description: 'Event Cascade Flow' },
] as const;

interface MfdModeSelectorProps {
  /** Currently selected mode */
  value: MfdMode;
  /** Callback when mode changes */
  onChange: (mode: MfdMode) => void;
  /** Override default mode options */
  modes?: readonly MfdModeOption[];
  /** Size of the toggle buttons */
  size?: 'small' | 'medium' | 'large';
  /** Disable the selector */
  disabled?: boolean;
  /** Custom aria-label for the button group */
  ariaLabel?: string;
}

const StyledToggleButton = styled(ToggleButton)(({ theme }) => ({
  fontFamily: 'var(--font-header)',
  fontSize: '10px',
  padding: theme.spacing(0.25, 1),
  border: '1px solid var(--color-border)',
  color: 'var(--color-text-secondary)',
  textTransform: 'uppercase',
  minWidth: 40,
  '&.Mui-selected': {
    backgroundColor: 'var(--color-accent-primary)',
    color: 'var(--color-bg-base)',
    '&:hover': {
      backgroundColor: 'var(--color-accent-primary)',
    },
  },
  '&:hover': {
    backgroundColor: 'var(--color-bg-interactive)',
  },
  '&:focus-visible': {
    outline: '2px solid var(--color-accent-primary)',
    outlineOffset: '2px',
  },
  '&.Mui-disabled': {
    color: 'var(--color-text-dim)',
    borderColor: 'var(--color-border)',
    opacity: 0.5,
  },
}));

/**
 * MfdModeSelector Component
 *
 * A reusable toggle button group for selecting MFD display modes.
 * Designed for consistent styling across the dashboard.
 *
 * @example Basic usage
 * <MfdModeSelector value={mode} onChange={setMode} />
 *
 * @example With custom modes
 * const customModes = [
 *   { id: 'custom1', label: 'C1' },
 *   { id: 'custom2', label: 'C2' },
 * ];
 * <MfdModeSelector value={mode} onChange={setMode} modes={customModes} />
 */
const MfdModeSelector: React.FC<MfdModeSelectorProps> = React.memo(({
  value,
  onChange,
  modes = MFD_MODES,
  size = 'small',
  disabled = false,
  ariaLabel = 'MFD display mode',
}) => {
  const handleChange = (_: React.MouseEvent<HTMLElement>, newMode: MfdMode | null) => {
    // Prevent deselection - always keep a mode selected
    if (newMode !== null) {
      onChange(newMode);
    }
  };

  return (
    <ToggleButtonGroup
      value={value}
      exclusive
      onChange={handleChange}
      aria-label={ariaLabel}
      size={size}
    >
      {modes.map((mode) => (
        <StyledToggleButton
          key={mode.id}
          value={mode.id}
          aria-label={mode.label}
          title={mode.description}
          disabled={disabled}
        >
          {mode.label}
        </StyledToggleButton>
      ))}
    </ToggleButtonGroup>
  );
});

export default MfdModeSelector;
