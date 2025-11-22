import React, { useState } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Paper,
  Stack,
  useTheme,
  useMediaQuery,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Map as MapIcon,
  Timeline as ActivityIcon,
  People as PeopleIcon,
  Analytics as AnalyticsIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';
import { tokens } from '../../styles/tokens';

const MobileTabbedContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  height: '100vh',
}));

const DesktopLayout = styled(Box)(({ theme }) => ({
  display: 'block',
}));

const CompactTabs = styled(Tabs)(({ theme }) => ({
  minHeight: '48px',
  backgroundColor: theme.palette.background.paper,
  borderBottom: `1px solid ${theme.palette.divider}`,
  
  '& .MuiTab-root': {
    minHeight: '48px',
    fontSize: '0.75rem',
    minWidth: 'auto',
    padding: theme.spacing(1, 1.5),
    fontWeight: 500,
    transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
    
    '&.Mui-selected': {
      fontWeight: 600,
    },
  },
  
  '& .MuiTabs-indicator': {
    backgroundColor: theme.palette.primary.main,
    height: '3px',
  },
}));

const TabContent = styled(Box)(({ theme }) => ({
  flex: 1,
  padding: theme.spacing(1),
  overflow: 'auto',
  maxHeight: 'calc(100vh - 120px)',
  
  '&::-webkit-scrollbar': {
    width: '6px',
  },
  '&::-webkit-scrollbar-track': {
    background: tokens.colors.background.tertiary,
    borderRadius: '3px',
  },
  '&::-webkit-scrollbar-thumb': {
    background: theme.palette.primary.main,
    borderRadius: '3px',
    '&:hover': {
      background: theme.palette.primary.dark,
    },
  },
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
    timeline?: React.ReactNode[];
  };
}

const MobileTabbedDashboard: React.FC<MobileTabbedDashboardProps> = ({ 
  children, 
  components 
}) => {
  const theme = useTheme();
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

  const getPanelLabel = (component: React.ReactNode, fallback: string) => {
    if (React.isValidElement(component)) {
      if (component.props?.title) {
        return component.props.title as string;
      }
      if (component.props?.['data-role']) {
        return component.props['data-role'] as string;
      }
    }
    return fallback;
  };

  const renderPanel = (component: React.ReactNode, compIndex: number, tabLabel: string, key: string) => {
    const label = getPanelLabel(component, `${tabLabel} Panel ${compIndex + 1}`);
    const isHighPriorityOverview = tabLabel === 'Overview' && compIndex <= 2;

    if (isHighPriorityOverview) {
      return (
        <Paper
          key={key}
          elevation={0}
          sx={{
            overflow: 'hidden',
            backgroundColor: theme.palette.background.paper,
            border: `1px solid ${theme.palette.divider}`,
            borderRadius: theme.shape.borderRadius,
            transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        >
          {component}
        </Paper>
      );
    }

    return (
      <Accordion
        key={key}
        disableGutters
        defaultExpanded={false}
        sx={{
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: `${theme.shape.borderRadius}px`,
          backgroundColor: theme.palette.background.paper,
          '&:before': { display: 'none' },
        }}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />}>
          <Typography variant="subtitle2" fontWeight={600}>
            {label}
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          {component}
        </AccordionDetails>
      </Accordion>
    );
  };

  if (components?.essential === undefined && React.Children.count(children) > 0) {
    return <DesktopLayout>{children}</DesktopLayout>;
  }

  return (
    <MobileTabbedContainer>
      {/* Mobile Header */}
      <Box sx={{ 
        p: 1.5, 
        textAlign: 'center', 
        backgroundColor: theme.palette.background.paper,
        borderBottom: `1px solid ${theme.palette.divider}`,
      }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'primary.main' }}>
          Novel Engine M1
        </Typography>
        <Typography variant="caption" color="text.secondary">
          AI-Powered Story Creation
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
            {tab.components.map((component, compIndex) =>
              renderPanel(component, compIndex, tab.label, `${index}-${compIndex}`)
            )}
          </Stack>
        </TabPanel>
      ))}
    </MobileTabbedContainer>
  );
};

export default MobileTabbedDashboard;
