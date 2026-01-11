import React from 'react';
import { Tooltip, IconButton } from '@mui/material';
import { HelpOutline as HelpIcon } from '@mui/icons-material';

interface HelpTooltipProps {
  title: string;
  size?: 'small' | 'medium';
}

/**
 * 统一的帮助提示组件
 * 用于为复杂术语和功能提供即时说明
 */
export const HelpTooltip: React.FC<HelpTooltipProps> = ({
  title,
  size = 'small'
}) => {
  return (
    <Tooltip title={title} arrow placement="top">
      <IconButton
        size={size}
        sx={{
          ml: 0.5,
          padding: '2px',
          color: 'var(--color-text-tertiary)',
          '&:hover': {
            color: 'var(--color-primary)',
            bgcolor: 'transparent',
          },
        }}
        aria-label="帮助"
      >
        <HelpIcon fontSize="inherit" />
      </IconButton>
    </Tooltip>
  );
};
