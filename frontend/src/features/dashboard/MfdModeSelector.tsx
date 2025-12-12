import React from 'react';
import { ToggleButton, ToggleButtonGroup, styled } from '@mui/material';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import HubIcon from '@mui/icons-material/Hub';
import TimelineIcon from '@mui/icons-material/Timeline';
import StreamIcon from '@mui/icons-material/Stream';

export type MfdMode = 'analytics' | 'network' | 'timeline' | 'signals';

interface MfdModeSelectorProps {
    value: MfdMode;
    onChange: (mode: MfdMode) => void;
}

const StyledToggleButtonGroup = styled(ToggleButtonGroup)(() => ({
    '& .MuiToggleButton-root': {
        color: 'var(--color-text-dim)',
        borderColor: 'var(--color-border-subtle)',
        padding: '4px 8px',
        '&.Mui-selected': {
            color: 'var(--color-primary-light)',
            backgroundColor: 'var(--color-primary-dim)',
            '&:hover': {
                backgroundColor: 'var(--color-primary-dim)',
            },
        },
        '&:hover': {
            backgroundColor: 'var(--color-bg-interactive)',
        },
    },
}));

const MfdModeSelector: React.FC<MfdModeSelectorProps> = ({ value, onChange }) => {
    const handleFormat = (event: React.MouseEvent<HTMLElement>, newMode: MfdMode | null) => {
        if (newMode !== null) {
            onChange(newMode);
        }
    };

    return (
        <StyledToggleButtonGroup
            value={value}
            exclusive
            onChange={handleFormat}
            aria-label="MFD Mode"
            size="small"
        >
            <ToggleButton value="analytics" aria-label="analytics">
                <AnalyticsIcon fontSize="small" />
            </ToggleButton>
            <ToggleButton value="network" aria-label="network">
                <HubIcon fontSize="small" />
            </ToggleButton>
            <ToggleButton value="timeline" aria-label="timeline">
                <TimelineIcon fontSize="small" />
            </ToggleButton>
            <ToggleButton value="signals" aria-label="signals">
                <StreamIcon fontSize="small" />
            </ToggleButton>
        </StyledToggleButtonGroup>
    );
};

export default MfdModeSelector;
