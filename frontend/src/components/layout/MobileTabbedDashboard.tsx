import { useState } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Paper,
  Stack,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Map as MapIcon,
  Timeline as ActivityIcon,
  People as PeopleIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

const MobileTabbedContainer = styled(Box)(({ theme }) => ({
  display: 'none',
  height: '100vh',
  
  [theme.breakpoints.down('md')]: {
    display: 'flex',
    flexDirection: 'column',
  },
}));

const DesktopLayout = styled(Box)(({ theme }) => ({
  display: 'block',
  
  [theme.breakpoints.down('md')]: {
    display: 'none',
  },
}));

const CompactTabs = styled(Tabs)(({ theme }) => ({
  minHeight: '40px',
  backgroundColor: theme.palette.background.paper,
  borderBottom: `1px solid ${theme.palette.divider}`,
  
  '& .MuiTab-root': {
    minHeight: '40px',
    fontSize: '0.75rem',
    minWidth: 'auto',
    padding: theme.spacing(0.5, 1),
  },
}));

const TabContent = styled(Box)(({ theme }) => ({
  flex: 1,
  padding: theme.spacing(1),
  overflow: 'auto',
  maxHeight: 'calc(100vh - 120px)', // Account for header and tabs
}));

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`mobile-tabpanel-${index}`}
      aria-labelledby={`mobile-tab-${index}`}
    >
      {value === index && <TabContent>{children}</TabContent>}
    </div>
  );
}

interface MobileTabbedDashboardProps {
  children: React.ReactNode;
  components?: {
    essential?: React.ReactNode[];
    activity?: React.ReactNode[];
    characters?: React.ReactNode[];
    analytics?: React.ReactNode[];
  };
}

const MobileTabbedDashboard: React.FC<MobileTabbedDashboardProps> = ({ 
  children, 
  components 
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [activeTab, setActiveTab] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const tabs = [
    {
      label: 'Overview',
      icon: <MapIcon fontSize="small" />,
      components: [...(components?.essential || []), ...(components?.activity || []).slice(0, 1)],
    },
    {
      label: 'Activity',
      icon: <ActivityIcon fontSize="small" />,
      components: components?.activity || [],
    },
    {
      label: 'Story',
      icon: <PeopleIcon fontSize="small" />,
      components: [...(components?.characters || []), ...(components?.timeline || [])],
    },
    {
      label: 'Analytics',
      icon: <AnalyticsIcon fontSize="small" />,
      components: components?.analytics || [],
    },
  ];

  if (!isMobile) {
    return <DesktopLayout>{children}</DesktopLayout>;
  }

  return (
    <MobileTabbedContainer>
      {/* Mobile Header */}
      <Box sx={{ p: 1, textAlign: 'center', backgroundColor: 'background.paper' }}>
        <Typography variant="subtitle1" color="primary" fontWeight={600}>
          Novel Engine M1
        </Typography>
      </Box>

      {/* Tabs */}
      <CompactTabs
        value={activeTab}
        onChange={handleTabChange}
        variant="fullWidth"
        indicatorColor="primary"
      >
        {tabs.map((tab, index) => (
          <Tab
            key={index}
            icon={tab.icon}
            label={tab.label}
            id={`mobile-tab-${index}`}
            aria-controls={`mobile-tabpanel-${index}`}
          />
        ))}
      </CompactTabs>

      {/* Tab Content */}
      {tabs.map((tab, index) => (
        <TabPanel key={index} value={activeTab} index={index}>
          <Stack spacing={1}>
            {tab.components.map((component, compIndex) => (
              <Paper 
                key={`${index}-${compIndex}`} 
                elevation={1}
                sx={{ 
                  overflow: 'hidden',
                  '& > *': {
                    // Optimized height constraints for mobile - Overview tab needs more space for QuickActions
                    maxHeight: index === 0 ? '200px' : '220px', // Increased Overview tab height to fix QuickActions rendering
                  }
                }}
              >
                {component}
              </Paper>
            ))}
          </Stack>
        </TabPanel>
      ))}
    </MobileTabbedContainer>
  );
};

export default MobileTabbedDashboard;