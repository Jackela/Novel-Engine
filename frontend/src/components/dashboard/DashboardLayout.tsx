/**
 * DashboardLayout Component
 *
 * A responsive three-region layout for the dashboard with:
 * - Fixed-width sidebar (320px) for Engine controls
 * - Flexible main content area for World State
 * - Fixed-width aside (360px) for Insights
 *
 * Features:
 * - Collapsible panels with smooth animations
 * - Keyboard shortcuts for panel toggling
 * - Mobile responsive (tabbed layout)
 * - Accessibility compliant (ARIA roles/labels)
 */

import React, { useEffect, useCallback, useState } from 'react';
import { Box, Tabs, Tab, useMediaQuery, useTheme } from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';
import { styled } from '@mui/material/styles';

// Layout constants (following design tokens)
const SIDEBAR_WIDTH = 320;
const ASIDE_WIDTH = 360;
const LAYOUT_GAP = 24; // spacing.6
const LAYOUT_PADDING = 24; // spacing.6
const ANIMATION_DURATION = 250; // motion.duration.standard

export interface DashboardLayoutProps {
  /** Content for the left sidebar (Engine panel) */
  sidebar: React.ReactNode;
  /** Content for the main area (World panel) */
  main: React.ReactNode;
  /** Content for the right aside (Insights panel) */
  aside: React.ReactNode;
  /** Whether sidebar is visible (default: true) */
  sidebarOpen?: boolean;
  /** Whether aside is visible (default: true) */
  asideOpen?: boolean;
  /** Callback when sidebar visibility changes */
  onSidebarToggle?: (open: boolean) => void;
  /** Callback when aside visibility changes */
  onAsideToggle?: (open: boolean) => void;
  /** Additional className for the layout container */
  className?: string;
}

// Styled components
const LayoutContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: `${LAYOUT_GAP}px`,
  padding: `${LAYOUT_PADDING}px`,
  height: 'calc(100vh - var(--header-height, 64px))',
  overflow: 'hidden',
  width: '100%',
  position: 'relative',
  backgroundColor: theme.palette.background.default,
}));

const SidebarRegion = styled(motion.aside)<{ $isOpen: boolean }>(({ theme, $isOpen }) => ({
  width: $isOpen ? `${SIDEBAR_WIDTH}px` : 0,
  minWidth: $isOpen ? `${SIDEBAR_WIDTH}px` : 0,
  height: '100%',
  overflow: 'hidden',
  transition: `width ${ANIMATION_DURATION}ms cubic-bezier(0.4, 0, 0.2, 1)`,
  display: 'flex',
  flexDirection: 'column',
}));

const MainRegion = styled(Box)({
  flex: 1,
  height: '100%',
  minWidth: 0, // Crucial for flex child shrinking
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
});

const AsideRegion = styled(motion.aside)<{ $isOpen: boolean }>(({ theme, $isOpen }) => ({
  width: $isOpen ? `${ASIDE_WIDTH}px` : 0,
  minWidth: $isOpen ? `${ASIDE_WIDTH}px` : 0,
  height: '100%',
  overflow: 'hidden',
  transition: `width ${ANIMATION_DURATION}ms cubic-bezier(0.4, 0, 0.2, 1)`,
  display: 'flex',
  flexDirection: 'column',
}));

const ToggleButton = styled('button')(({ theme }) => ({
  background: 'transparent',
  border: `1px solid ${theme.palette.divider}`,
  color: theme.palette.text.secondary,
  padding: theme.spacing(0.25, 1), // 2px 8px
  borderRadius: theme.spacing(0.5), // 4px
  cursor: 'pointer',
  fontFamily: '"JetBrains Mono", monospace',
  fontSize: '9px',
  textTransform: 'uppercase',
  transition: 'all 150ms ease',
  flexShrink: 0,
  '&:hover': {
    borderColor: theme.palette.primary.main,
    color: theme.palette.primary.main,
  },
  '&:focus-visible': {
    outline: `2px solid ${theme.palette.primary.main}`,
    outlineOffset: '2px',
  },
}));

const RegionHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: theme.spacing(1, 1.5), // 8px 12px
  borderBottom: `1px solid ${theme.palette.divider}`,
  background: 'rgba(0, 0, 0, 0.2)',
  marginBottom: theme.spacing(1.5), // 12px
  borderRadius: `${theme.spacing(0.5)} ${theme.spacing(0.5)} 0 0`, // 4px 4px 0 0
}));

const RegionTitle = styled('span')(({ theme }) => ({
  fontFamily: '"JetBrains Mono", monospace',
  fontSize: '11px',
  fontWeight: 600,
  textTransform: 'uppercase',
  color: theme.palette.text.secondary,
  letterSpacing: '0.5px',
}));

const ShowPanelButton = styled('button')(({ theme }) => ({
  position: 'absolute',
  top: '50%',
  transform: 'translateY(-50%)',
  background: theme.palette.background.paper,
  border: `1px solid ${theme.palette.divider}`,
  color: theme.palette.text.secondary,
  padding: theme.spacing(1, 0.75), // 8px 6px
  borderRadius: theme.spacing(0.5), // 4px
  cursor: 'pointer',
  fontFamily: '"JetBrains Mono", monospace',
  fontSize: '10px',
  textTransform: 'uppercase',
  zIndex: 100,
  transition: 'all 150ms ease',
  writingMode: 'vertical-rl',
  textOrientation: 'mixed',
  '&:hover': {
    borderColor: theme.palette.primary.main,
    color: theme.palette.primary.main,
  },
  '&:focus-visible': {
    outline: `2px solid ${theme.palette.primary.main}`,
    outlineOffset: '2px',
  },
}));

// Visually hidden component for screen reader-only content
const VisuallyHidden = styled('span')({
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
});

// Mobile tabbed layout
const MobileContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  height: 'calc(100vh - var(--header-height, 64px))',
  overflow: 'hidden',
  backgroundColor: theme.palette.background.default,
}));

const TabContent = styled(Box)(({ theme }) => ({
  flex: 1,
  overflow: 'auto',
  padding: theme.spacing(2), // 16px
}));

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <TabContent
      role="tabpanel"
      hidden={value !== index}
      id={`dashboard-tabpanel-${index}`}
      aria-labelledby={`dashboard-tab-${index}`}
    >
      {value === index && children}
    </TabContent>
  );
};

const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  sidebar,
  main,
  aside,
  sidebarOpen = true,
  asideOpen = true,
  onSidebarToggle,
  onAsideToggle,
  className,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileTab, setMobileTab] = useState(1); // Default to World (main)

  // Keyboard shortcuts handler
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Cmd/Ctrl + [ to toggle sidebar
      if ((event.metaKey || event.ctrlKey) && event.key === '[') {
        event.preventDefault();
        onSidebarToggle?.(!sidebarOpen);
      }
      // Cmd/Ctrl + ] to toggle aside
      if ((event.metaKey || event.ctrlKey) && event.key === ']') {
        event.preventDefault();
        onAsideToggle?.(!asideOpen);
      }
    },
    [sidebarOpen, asideOpen, onSidebarToggle, onAsideToggle]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Mobile tabbed layout
  if (isMobile) {
    return (
      <MobileContainer className={`dashboard-layout dashboard-layout--mobile ${className || ''}`}>
        <Tabs
          value={mobileTab}
          onChange={(_, newValue) => setMobileTab(newValue)}
          variant="fullWidth"
          aria-label="Dashboard sections"
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            backgroundColor: 'background.paper',
          }}
        >
          <Tab label="Engine" id="dashboard-tab-0" aria-controls="dashboard-tabpanel-0" />
          <Tab label="World" id="dashboard-tab-1" aria-controls="dashboard-tabpanel-1" />
          <Tab label="Insights" id="dashboard-tab-2" aria-controls="dashboard-tabpanel-2" />
        </Tabs>

        <TabPanel value={mobileTab} index={0}>
          {sidebar}
        </TabPanel>
        <TabPanel value={mobileTab} index={1}>
          {main}
        </TabPanel>
        <TabPanel value={mobileTab} index={2}>
          {aside}
        </TabPanel>
      </MobileContainer>
    );
  }

  // Desktop three-column layout
  return (
    <LayoutContainer className={`dashboard-layout ${className || ''}`}>
      {/* Toggle buttons for hidden panels */}
      {!sidebarOpen && (
        <ShowPanelButton
          onClick={() => onSidebarToggle?.(true)}
          aria-label="Show engine panel"
          style={{ left: '0px' }}
        >
          Engine ▶
        </ShowPanelButton>
      )}
      {!asideOpen && (
        <ShowPanelButton
          onClick={() => onAsideToggle?.(true)}
          aria-label="Show insights panel"
          style={{ right: '0px' }}
        >
          ◀ Insights
        </ShowPanelButton>
      )}

      {/* Sidebar (Engine) */}
      <AnimatePresence initial={false}>
        <SidebarRegion
          $isOpen={sidebarOpen}
          role="complementary"
          aria-label="Engine panel"
          aria-hidden={!sidebarOpen}
          data-state={sidebarOpen ? 'open' : 'closing'}
          className="dashboard-sidebar"
          initial={false}
          animate={{ width: sidebarOpen ? SIDEBAR_WIDTH : 0 }}
          transition={{ duration: ANIMATION_DURATION / 1000, ease: [0.4, 0, 0.2, 1] }}
        >
          {sidebarOpen && (
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <RegionHeader>
                <RegionTitle>Engine</RegionTitle>
                <ToggleButton
                  onClick={() => onSidebarToggle?.(false)}
                  aria-label="Hide engine panel"
                  aria-describedby="shortcut-sidebar"
                >
                  Hide ▶
                </ToggleButton>
                <VisuallyHidden id="shortcut-sidebar">
                  Press Cmd+[ or Ctrl+[ to toggle
                </VisuallyHidden>
              </RegionHeader>
              <Box sx={{ flex: 1, pr: 1, overflowY: 'auto' }}>
                {sidebar}
              </Box>
            </Box>
          )}
        </SidebarRegion>
      </AnimatePresence>

      {/* Main (World) */}
      <MainRegion role="main" className="dashboard-main">
        {main}
      </MainRegion>

      {/* Aside (Insights) */}
      <AnimatePresence initial={false}>
        <AsideRegion
          $isOpen={asideOpen}
          role="complementary"
          aria-label="Insights panel"
          aria-hidden={!asideOpen}
          data-state={asideOpen ? 'open' : 'closing'}
          className="dashboard-aside"
          initial={false}
          animate={{ width: asideOpen ? ASIDE_WIDTH : 0 }}
          transition={{ duration: ANIMATION_DURATION / 1000, ease: [0.4, 0, 0.2, 1] }}
        >
          {asideOpen && (
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <RegionHeader>
                <RegionTitle>Insights</RegionTitle>
                <ToggleButton
                  onClick={() => onAsideToggle?.(false)}
                  aria-label="Hide insights panel"
                  aria-describedby="shortcut-aside"
                >
                  ◀ Hide
                </ToggleButton>
                <VisuallyHidden id="shortcut-aside">
                  Press Cmd+] or Ctrl+] to toggle
                </VisuallyHidden>
              </RegionHeader>
              <Box sx={{ flex: 1, pl: 1, overflowY: 'auto' }}>
                {aside}
              </Box>
            </Box>
          )}
        </AsideRegion>
      </AnimatePresence>
    </LayoutContainer>
  );
};

export default DashboardLayout;
