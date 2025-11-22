
import React, { useState, useEffect } from 'react';
import { Box, Alert, Snackbar, useMediaQuery, Stack, useTheme } from '@mui/material';
import { AnimatePresence, motion } from 'framer-motion';
import CommandLayout from '../layout/CommandLayout';
import MobileTabbedDashboard from '../layout/MobileTabbedDashboard';
import { logger } from '../../services/logging/LoggerFactory';
import QuickActions, { type QuickAction } from './QuickActions';
import CommandTopBar from '../layout/CommandTopBar';

// Import new panels
import EnginePanel from './panels/EnginePanel';
import WorldPanel from './panels/WorldPanel';
import InsightsPanel from './panels/InsightsPanel';

type PipelineState = 'idle' | 'running' | 'paused' | 'stopped';

interface DashboardProps {
  userId?: string;
  campaignId?: string;
}

const Dashboard: React.FC<DashboardProps> = ({ userId: _userId, campaignId: _campaignId }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [loading, setLoading] = useState(false);
  const [error, _setError] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [pipelineStatus, setPipelineStatus] = useState<PipelineState>('idle');
  const [isLiveMode, setIsLiveMode] = useState(false);
  const [isOnline, setIsOnline] = useState(() => {
    if (typeof navigator === 'undefined') return true;
    return navigator.onLine;
  });

  useEffect(() => {
    const interval = setInterval(() => setLastUpdate(new Date()), 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const handleOnline = () => { setIsOnline(true); showNotification('Connection restored.'); };
    const handleOffline = () => { setIsOnline(false); setIsLiveMode(false); showNotification('Connection lost.'); };
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const showNotification = (message: string) => {
    setSnackbarMessage(message);
    setSnackbarOpen(true);
  };

  const handleQuickAction = (action: QuickAction) => {
    logger.info('Quick action triggered:', { action });
    switch (action) {
      case 'play': setPipelineStatus('running'); setIsLiveMode(true); showNotification('System resumed'); break;
      case 'pause': setPipelineStatus('paused'); setIsLiveMode(false); showNotification('System paused'); break;
      case 'stop': setPipelineStatus('stopped'); setIsLiveMode(false); showNotification('System stopped'); break;
      case 'refresh': 
        setLoading(true); 
        setTimeout(() => { setLoading(false); setLastUpdate(new Date()); showNotification('Data refreshed'); }, 1000); 
        break;
      default: showNotification(`Action ${action} triggered`);
    }
  };

  const handleSnackbarClose = () => setSnackbarOpen(false);

  // --- LAYOUT SECTIONS ---

  // --- STATE ---
  const [mfdMode, setMfdMode] = useState<'analytics' | 'network' | 'timeline' | 'signals'>('analytics');
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [isMapExpanded, setIsMapExpanded] = useState(false);

  // --- ANIMATION VARIANTS ---
  const panelVariants = {
    open: { 
      width: '25%', 
      opacity: 1,
      transition: { type: 'spring', stiffness: 300, damping: 30 }
    },
    closed: { 
      width: 0, 
      opacity: 0,
      transition: { type: 'spring', stiffness: 300, damping: 30 }
    }
  };

  // Mobile Layout (Tabbed)
  if (isMobile) {
    return (
      <CommandLayout>
        <CommandTopBar 
          pipelineStatus={pipelineStatus} 
          isOnline={isOnline} 
          isLive={isLiveMode} 
          lastUpdate={lastUpdate} 
        />
        <MobileTabbedDashboard components={{
          essential: [
            <Box key="pipeline" sx={{ mb: 2 }}>
              <EnginePanel 
                loading={loading} 
                error={!!error} 
                pipelineStatus={pipelineStatus} 
                isLive={isLiveMode} 
                onClose={() => setLeftPanelOpen(false)}
              />
            </Box>,
            <Box key="actions" sx={{ mb: 2 }}>
              <QuickActions status={pipelineStatus} isLive={isLiveMode} isOnline={isOnline} onAction={handleQuickAction} variant="tile" />
            </Box>
          ],
          activity: [
            <Box key="world">
              <WorldPanel loading={loading} error={!!error} onExpand={() => setIsMapExpanded(true)} />
            </Box>
          ],
          analytics: [
            <Box key="insights">
              <InsightsPanel 
                loading={loading} 
                error={!!error} 
                pipelineStatus={pipelineStatus} 
                isLive={isLiveMode} 
                isOnline={isOnline}
                mfdMode={mfdMode}
                onMfdModeChange={setMfdMode}
                onQuickAction={handleQuickAction}
                onClose={() => setRightPanelOpen(false)}
              />
            </Box>
          ]
        }}>
          <></>
        </MobileTabbedDashboard>
      </CommandLayout>
    );
  }

  return (
    <CommandLayout>
      <CommandTopBar 
        pipelineStatus={pipelineStatus} 
        isOnline={isOnline} 
        isLive={isLiveMode} 
        lastUpdate={lastUpdate} 
      />
      
      {/* View Controls (Floating or Integrated) - Only visible if a panel is closed */}
      {(!leftPanelOpen || !rightPanelOpen) && (
        <div style={{ position: 'absolute', top: 'calc(var(--header-height) + 10px)', left: '50%', transform: 'translateX(-50%)', zIndex: 100, display: 'flex', gap: '8px' }}>
          {!leftPanelOpen && (
            <button 
              onClick={() => setLeftPanelOpen(true)}
              style={{ background: 'var(--color-bg-panel)', border: '1px solid var(--color-accent-primary)', color: 'var(--color-accent-primary)', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontFamily: 'var(--font-header)', fontSize: '10px' }}
            >
              SHOW ENGINE
            </button>
          )}
          {!rightPanelOpen && (
            <button 
              onClick={() => setRightPanelOpen(true)}
              style={{ background: 'var(--color-bg-panel)', border: '1px solid var(--color-accent-primary)', color: 'var(--color-accent-primary)', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontFamily: 'var(--font-header)', fontSize: '10px' }}
            >
              SHOW INSIGHTS
            </button>
          )}
        </div>
      )}

      {/* Main Content Area - Flexbox for smooth animation */}
      <Box 
        sx={{ 
          p: 3, 
          display: 'flex', // Changed from Grid to Flex for animation
          gap: 3,
          height: 'calc(100vh - var(--header-height))',
          overflow: 'hidden',
          width: '100%',
          position: 'relative'
        }}
      >
        {/* Left Column: Engine */}
        <AnimatePresence initial={false}>
          {leftPanelOpen && (
            <motion.div
              initial="open"
              animate="open"
              exit="closed"
              variants={panelVariants}
              style={{ overflow: 'hidden', height: '100%' }}
            >
              <Box sx={{ height: '100%', pr: 1, overflowY: 'auto' }}>
                <EnginePanel 
                  loading={loading} 
                  error={!!error} 
                  pipelineStatus={pipelineStatus} 
                  isLive={isLiveMode} 
                  onClose={() => setLeftPanelOpen(false)}
                />
              </Box>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Center Column: World */}
        <motion.div 
          layout 
          style={{ flex: 1, height: '100%', minWidth: 0 }} // minWidth 0 is crucial for flex child shrinking
        >
          <Box sx={{ height: '100%', overflow: 'hidden' }}>
            <WorldPanel loading={loading} error={!!error} onExpand={() => setIsMapExpanded(true)} />
          </Box>
        </motion.div>

        {/* Right Column: Insights */}
        <AnimatePresence initial={false}>
          {rightPanelOpen && (
            <motion.div
              initial="open"
              animate="open"
              exit="closed"
              variants={panelVariants}
              style={{ overflow: 'hidden', height: '100%' }}
            >
              <Box sx={{ height: '100%', pl: 1, overflowY: 'auto' }}>
                <InsightsPanel 
                  loading={loading} 
                  error={!!error} 
                  pipelineStatus={pipelineStatus} 
                  isLive={isLiveMode} 
                  isOnline={isOnline}
                  mfdMode={mfdMode}
                  onMfdModeChange={setMfdMode}
                  onQuickAction={handleQuickAction}
                  onClose={() => setRightPanelOpen(false)}
                />
              </Box>
            </motion.div>
          )}
        </AnimatePresence>
      </Box>

      {/* Map Overlay (Full Screen) */}
      <AnimatePresence>
        {isMapExpanded && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 2000,
              background: 'var(--color-bg-base)',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            {/* Overlay Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ fontFamily: 'var(--font-header)', fontSize: '24px', color: 'var(--color-accent-primary)' }}>WORLD STATE // INSPECT MODE</span>
              <button 
                onClick={() => setIsMapExpanded(false)}
                style={{ 
                  background: 'transparent', 
                  border: '1px solid var(--color-border)', 
                  color: 'var(--color-text-primary)', 
                  padding: '8px 16px', 
                  cursor: 'pointer', 
                  fontFamily: 'var(--font-header)'
                }}
              >
                CLOSE OVERLAY [ESC]
              </button>
            </div>
            
            {/* Full Map Content */}
            <Box sx={{ flex: 1, border: '1px solid var(--color-border)', borderRadius: '8px', overflow: 'hidden' }}>
               <WorldStateMap loading={loading} error={!!error} />
            </Box>
          </motion.div>
        )}
      </AnimatePresence>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleSnackbarClose} severity="info" variant="filled" sx={{ borderRadius: 2 }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </CommandLayout>
  );
};

export default Dashboard;
