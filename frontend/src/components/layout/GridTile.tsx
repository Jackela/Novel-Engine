import { Paper, Box, Typography, IconButton, useTheme, useMediaQuery } from '@mui/material';
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
  position: GridPosition;
  children: React.ReactNode;
  loading?: boolean;
  error?: boolean;
  onMenuClick?: () => void;
  className?: string;
  'data-testid'?: string;
}

const StyledPaper = styled(Paper, {
  shouldForwardProp: (prop) => !['position', 'currentBreakpoint'].includes(prop as string),
})<{ position: GridPosition; currentBreakpoint: 'desktop' | 'tablet' | 'mobile' }>(
  ({ theme, position, currentBreakpoint }) => {
    const getGridStyles = () => {
      const breakpointPos = position[currentBreakpoint];
      
      const styles: Record<string, any> = {
        gridColumn: breakpointPos.column || 'auto',
      };
      
      if (breakpointPos.row) {
        styles.gridRow = breakpointPos.row;
      }
      
      if (breakpointPos.height) {
        styles.height = breakpointPos.height;
      } else {
        // Default heights for different breakpoints
        if (currentBreakpoint === 'desktop') {
          styles.minHeight = '320px';
        } else if (currentBreakpoint === 'tablet') {
          styles.minHeight = '280px';
        } else {
          styles.minHeight = '200px';
        }
      }
      
      return styles;
    };

    return {
      ...getGridStyles(),
      position: 'relative',
      overflow: 'hidden',
      border: '1px solid #2a2a30',
      borderRadius: theme.shape.borderRadius,
      backgroundColor: '#111113',
      transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
      
      '&:hover': {
        backgroundColor: '#1a1a1d',
        borderColor: '#6366f1',
        transform: 'translateY(-2px)',
        boxShadow: '0 4px 8px rgba(99, 102, 241, 0.2)',
      },
    };
  }
);

const TileHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: theme.spacing(2, 2, 1),
  borderBottom: '1px solid #2a2a30',
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
    background: '#1a1a1d',
    borderRadius: '3px',
  },
  '&::-webkit-scrollbar-thumb': {
    background: '#6366f1',
    borderRadius: '3px',
    '&:hover': {
      background: '#4f46e5',
    },
  },
  
  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(1),
  },
}));

const LoadingOverlay = styled(Box)(({ theme }) => ({
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
}));

const GridTile: React.FC<GridTileProps> = ({
  title,
  position,
  children,
  loading = false,
  error = false,
  onMenuClick,
  className,
  'data-testid': testId,
}) => {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg'));
  const isTablet = useMediaQuery(theme.breakpoints.between('md', 'lg'));
  
  const currentBreakpoint = isDesktop ? 'desktop' : isTablet ? 'tablet' : 'mobile';

  return (
    <StyledPaper 
      position={position} 
      currentBreakpoint={currentBreakpoint}
      className={className}
      elevation={1}
      data-testid={testId}
    >
      <TileHeader>
        <Typography variant="h6" component="h2" fontWeight={600}>
          {title}
        </Typography>
        {onMenuClick && (
          <IconButton size="small" onClick={onMenuClick} edge="end">
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