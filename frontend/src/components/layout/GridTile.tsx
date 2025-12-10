import React from 'react';
import { Paper, Box, Typography, IconButton, useTheme, useMediaQuery } from '@mui/material';
import type { CSSProperties } from 'react';
import type { SxProps } from '@mui/system';
import type { Theme } from '@mui/material/styles';
import { styled } from '@mui/material/styles';
import { MoreVert as MoreIcon } from '@mui/icons-material';
import { tokens } from '@/styles/tokens';

interface GridPosition {
  desktop: {
    column: string;
    row?: string;
    height?: string;
  };
  tablet: {
    column: string;
    row?: string;
    height?: string;
  };
  mobile: {
    column?: string;
    row?: string;
    height?: string;
  };
}

interface GridTileProps {
  title: string;
  position?: GridPosition;
  children: React.ReactNode;
  loading?: boolean;
  error?: boolean;
  onMenuClick?: () => void;
  headerAction?: React.ReactNode;
  className?: string;
  'data-testid'?: string;
  'data-role'?: string;
  sx?: SxProps<Theme> | undefined;
}

const StyledPaper = styled(Paper, {
  shouldForwardProp: (prop) => !['position', 'currentBreakpoint'].includes(prop as string),
})<{ position: GridPosition; currentBreakpoint: 'desktop' | 'tablet' | 'mobile' }>(
  ({ theme, position, currentBreakpoint }) => {
    const getGridStyles = () => {
      const breakpointPos = position?.[currentBreakpoint];

      const styles: Partial<CSSProperties> = {
        gridColumn: breakpointPos?.column || 'auto',
      };

      if (breakpointPos?.row) {
        styles.gridRow = breakpointPos.row;
      }

      if (breakpointPos?.height) {
        styles.minHeight = breakpointPos.height;
        styles.height = breakpointPos.height;
      } else {
        if (currentBreakpoint === 'desktop') {
          styles.minHeight = '260px';
        } else if (currentBreakpoint === 'tablet') {
          styles.minHeight = '220px';
        } else {
          styles.minHeight = '180px';
        }
      }

      return styles;
    };

    return {
      ...getGridStyles(),
      position: 'relative',
      overflow: 'hidden',
      // VisionOS Glass Panel
      ...tokens.glass.panel,
      borderRadius: theme.shape.borderRadius * 2,
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      '&:hover': {
        borderColor: tokens.colors.border.hover,
        boxShadow: tokens.elevation.lg,
      }
    };
  }
);

const TileHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: theme.spacing(2, 2.5, 1.5),
  borderBottom: tokens.glass.border,
  minHeight: '60px',

  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(1.5, 2, 1),
  },
}));

const TileContent = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2.5),
  height: 'calc(100% - 60px)',
  overflow: 'auto',

  '&::-webkit-scrollbar': {
    width: '6px',
    height: '6px',
  },
  '&::-webkit-scrollbar-track': {
    background: 'transparent',
  },
  '&::-webkit-scrollbar-thumb': {
    background: tokens.colors.border.tertiary,
    borderRadius: '3px',
    '&:hover': {
      background: tokens.colors.primary[600],
    },
  },

  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(1.5),
  },
}));

const LoadingOverlay = styled(Box)({
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(10, 10, 11, 0.6)',
  backdropFilter: 'blur(8px)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 10,
});

const GridTile: React.FC<GridTileProps> = ({
  title,
  position,
  children,
  loading = false,
  error = false,
  onMenuClick,
  headerAction,
  className,
  'data-testid': testId,
  'data-role': role,
  sx,
}) => {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg'));
  const isTablet = useMediaQuery(theme.breakpoints.between('md', 'lg'));

  const currentBreakpoint = isDesktop ? 'desktop' : isTablet ? 'tablet' : 'mobile';
  const resolvedPosition: GridPosition = position ?? {
    desktop: { column: 'auto' },
    tablet: { column: 'auto' },
    mobile: { column: 'auto' },
  };

  return (
    <StyledPaper
      position={resolvedPosition}
      currentBreakpoint={currentBreakpoint}
      className={className ?? ''}
      elevation={0}
      data-testid={testId}
      data-role={role}
      sx={sx as SxProps<Theme>}
    >
      <TileHeader>
        <Typography variant="h6" component="h2" fontWeight={600} sx={{ letterSpacing: '0.02em', color: tokens.colors.text.primary }}>
          {title}
        </Typography>
        <Box display="flex" alignItems="center" gap={1}>
          {headerAction}
          {onMenuClick && (
            <IconButton
              size="small"
              onClick={onMenuClick}
              edge="end"
              aria-label={`${title} options`}
              sx={{ color: tokens.colors.text.secondary }}
            >
              <MoreIcon />
            </IconButton>
          )}
        </Box>
      </TileHeader>

      <TileContent>
        {error ? (
          <Box
            display="flex"
            alignItems="center"
            justifyContent="center"
            height="100%"
            color={tokens.colors.status.error.main}
          >
            <Typography variant="body2">Error loading data</Typography>
          </Box>
        ) : (
          children
        )}
      </TileContent>

      {loading && (
        <LoadingOverlay>
          <Typography variant="body2" color="text.secondary">Loading...</Typography>
        </LoadingOverlay>
      )}
    </StyledPaper>
  );
};

export default GridTile;