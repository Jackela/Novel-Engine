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
      border: `1px solid ${theme.palette.divider}`,
      borderRadius: theme.spacing(1.5),
      backgroundColor: theme.palette.background.paper,
      transition: 'box-shadow 0.2s ease-in-out',
      
      '&:hover': {
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
}));

const TileContent = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  height: 'calc(100% - 56px)',
  overflow: 'auto',
  
  // Mobile: reduced padding to maximize content space
  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(1), // Reduced from 2 to 1 for mobile
  },
}));

const LoadingOverlay = styled(Box)(({ theme }) => ({
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(255, 255, 255, 0.8)',
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