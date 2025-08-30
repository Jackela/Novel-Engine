import React, { useState } from 'react';
import {
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Chip,
  Stack,
  Badge,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Map as MapIcon,
  Timeline as ActivityIcon,
  People as PeopleIcon,
  AutoStories as StoryIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

const MobileOrganizer = styled(Box)(({ theme }) => ({
  display: 'none',
  
  [theme.breakpoints.down('md')]: {
    display: 'block',
  },
}));

const DesktopLayout = styled(Box)(({ theme }) => ({
  display: 'block',
  
  [theme.breakpoints.down('md')]: {
    display: 'none',
  },
}));

const CompactAccordion = styled(Accordion)(({ theme }) => ({
  marginBottom: theme.spacing(0.5),
  borderRadius: theme.spacing(1),
  border: `1px solid ${theme.palette.divider}`,
  '&:before': {
    display: 'none',
  },
  '&.Mui-expanded': {
    margin: `${theme.spacing(0.5)} 0`,
  },
}));

const CompactAccordionSummary = styled(AccordionSummary)(({ theme }) => ({
  minHeight: '48px',
  padding: theme.spacing(0, 2),
  '&.Mui-expanded': {
    minHeight: '48px',
  },
  '& .MuiAccordionSummary-content': {
    alignItems: 'center',
    margin: theme.spacing(1, 0),
    '&.Mui-expanded': {
      margin: theme.spacing(1, 0),
    },
  },
}));

const CompactAccordionDetails = styled(AccordionDetails)(({ theme }) => ({
  padding: theme.spacing(0, 1, 1, 1),
}));

interface MobileDashboardOrganizerProps {
  children: React.ReactNode;
  components?: {
    essential?: React.ReactNode[];
    activity?: React.ReactNode[];
    characters?: React.ReactNode[];
    timeline?: React.ReactNode[];
    analytics?: React.ReactNode[];
  };
}

interface SectionConfig {
  id: string;
  title: string;
  icon: React.ReactNode;
  badge?: string;
  defaultExpanded?: boolean;
  priority: 'high' | 'medium' | 'low';
}

const MobileDashboardOrganizer: React.FC<MobileDashboardOrganizerProps> = ({ 
  children, 
  components 
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['essential', 'activity']) // Default expanded sections
  );

  const sections: SectionConfig[] = [
    {
      id: 'essential',
      title: 'Map & Controls',
      icon: <MapIcon fontSize="small" />,
      badge: 'Always Visible',
      defaultExpanded: true,
      priority: 'high',
    },
    {
      id: 'activity',
      title: 'System Status',
      icon: <ActivityIcon fontSize="small" />,
      badge: 'Live Data',
      defaultExpanded: true,
      priority: 'high',
    },
    {
      id: 'characters',
      title: 'Characters & Events',
      icon: <PeopleIcon fontSize="small" />,
      badge: '5 Active',
      priority: 'medium',
    },
    {
      id: 'timeline',
      title: 'Narrative Arc',
      icon: <StoryIcon fontSize="small" />,
      badge: '31% Complete',
      priority: 'medium',
    },
    {
      id: 'analytics',
      title: 'Analytics',
      icon: <AnalyticsIcon fontSize="small" />,
      badge: 'Quality Metrics',
      priority: 'low',
    },
  ];

  const handleSectionToggle = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const getSectionComponents = (sectionId: string): React.ReactNode[] => {
    return components?.[sectionId as keyof typeof components] || [];
  };

  if (!isMobile) {
    return <DesktopLayout>{children}</DesktopLayout>;
  }

  return (
    <MobileOrganizer>
      <Box sx={{ p: 1 }}>
        {/* Mobile Header */}
        <Box sx={{ mb: 2, textAlign: 'center' }}>
          <Typography variant="h6" color="primary" gutterBottom>
            Emergent Narrative Dashboard
          </Typography>
          <Stack direction="row" spacing={1} justifyContent="center">
            <Chip 
              label="Mobile View" 
              size="small" 
              color="primary" 
              variant="outlined" 
            />
            <Chip 
              label={`${expandedSections.size}/${sections.length} Sections`}
              size="small" 
              variant="outlined" 
            />
          </Stack>
        </Box>

        {/* Essential Section - Always Visible */}
        <Box sx={{ mb: 2 }}>
          {getSectionComponents('essential').map((component, index) => (
            <Box key={`essential-${index}`} sx={{ mb: 1 }}>
              {component}
            </Box>
          ))}
        </Box>

        {/* Collapsible Sections */}
        {sections.slice(1).map((section) => (
          <CompactAccordion
            key={section.id}
            expanded={expandedSections.has(section.id)}
            onChange={() => handleSectionToggle(section.id)}
            elevation={1}
          >
            <CompactAccordionSummary
              expandIcon={<ExpandMoreIcon />}
              sx={{
                backgroundColor: section.priority === 'high' 
                  ? theme.palette.primary.main + '08'
                  : section.priority === 'medium'
                  ? theme.palette.warning.main + '06'
                  : theme.palette.action.hover,
              }}
            >
              <Stack 
                direction="row" 
                spacing={1.5} 
                alignItems="center" 
                sx={{ flex: 1 }}
              >
                <Box sx={{ color: theme.palette.text.secondary }}>
                  {section.icon}
                </Box>
                <Typography 
                  variant="subtitle2" 
                  fontWeight={600}
                  sx={{ flex: 1 }}
                >
                  {section.title}
                </Typography>
                {section.badge && (
                  <Chip
                    label={section.badge}
                    size="small"
                    variant="outlined"
                    sx={{ 
                      height: '24px', 
                      fontSize: '0.7rem',
                      color: section.priority === 'high' 
                        ? theme.palette.primary.main 
                        : theme.palette.text.secondary
                    }}
                  />
                )}
              </Stack>
            </CompactAccordionSummary>
            
            <CompactAccordionDetails>
              <Stack spacing={1}>
                {getSectionComponents(section.id).map((component, index) => (
                  <Box key={`${section.id}-${index}`}>
                    {component}
                  </Box>
                ))}
              </Stack>
            </CompactAccordionDetails>
          </CompactAccordion>
        ))}

        {/* Mobile Footer */}
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Tap sections to expand • Optimized for mobile
          </Typography>
        </Box>
      </Box>
    </MobileOrganizer>
  );
};

export default MobileDashboardOrganizer;