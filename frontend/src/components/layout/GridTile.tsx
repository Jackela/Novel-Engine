import { Paper, Box, Typography, IconButton, useTheme, useMediaQuery } from '@mui/material';
import type { CSSProperties } from 'react';
import type { SxProps } from '@mui/system';
import type { Theme } from '@mui/material/styles';
import { styled } from '@mui/material/styles';
import { MoreVert as MoreIcon } from '@mui/icons-material';

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
        // Default heights for different breakpoints
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
      border: `1px solid ${theme.palette.divider}`,
      borderRadius: theme.shape.borderRadius,
      backgroundColor: theme.palette.background.paper,
      transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
      
      '&:hover': {
        backgroundColor: theme.palette.background.default,
        borderColor: theme.palette.primary.main,
        transform: 'translateY(-2px)',
        boxShadow: theme.shadows[4],
      },
    };
  }
);

const TileHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: theme.spacing(2, 2, 1),
  borderBottom: `1px solid ${theme.palette.divider}`,
  minHeight: '56px',
  
  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(1.5, 1.5, 1),
  },
}));

const TileContent = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  height: 'calc(100% - 56px)',
  overflow: 'auto',
  
  '&::-webkit-scrollbar': {
    width: '6px',
    height: '6px',
  },
  '&::-webkit-scrollbar-track': {
    background: theme.palette.background.default,
    borderRadius: '3px',
  },
  '&::-webkit-scrollbar-thumb': {
    background: theme.palette.primary.main,
    borderRadius: '3px',
    '&:hover': {
      background: theme.palette.primary.dark,
    },
  },
  
  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(1),
  },
}));

const LoadingOverlay = styled(Box)({
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(10, 10, 11, 0.9)',
  backdropFilter: 'blur(4px)',
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
      elevation={1}
      data-testid={testId}
      data-role={role}
      sx={sx as SxProps<Theme>}
    >
      <TileHeader>
        <Typography variant="h6" component="h2" fontWeight={600}>
          {title}
        </Typography>
        {onMenuClick && (
          <IconButton
            size="small"
            onClick={onMenuClick}
            edge="end"
            aria-label={`${title} options`}
          >
            <MoreIcon />
          </IconButton>
        )}
      </TileHeader>
      
      <TileContent>
        {error ? (
          <Box 
            display="flex" 
            alignItems="center" 
            justifyContent="center" 
            height="100%"
            color="error.main"
          >
            <Typography variant="body2">Error loading data</Typography>
          </Box>
        ) : (
          children
        )}
      </TileContent>
      
      {loading && (
        <LoadingOverlay>
          <Typography variant="body2">Loading...</Typography>
        </LoadingOverlay>
      )}
    </StyledPaper>
  );
};

export default GridTile;
