import React from 'react';
import { Box } from '@mui/material';
import WorldStateMap from '../WorldStateMapV2';

interface WorldPanelProps {
  loading: boolean;
  error: boolean;
  onExpand?: () => void;
}

const WorldPanel: React.FC<WorldPanelProps> = React.memo(({ loading, error, onExpand }) => {
  return (
    <Box className="command-panel" sx={{ height: '100%', p: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column', position: 'relative' }}>
       {/* Map Header Overlay */}
       <div style={{ 
         position: 'absolute', 
         top: 0, 
         left: 0, 
         right: 0, 
         height: '48px', 
         display: 'flex', 
         alignItems: 'center', 
         justifyContent: 'space-between', 
         padding: '0 16px', 
         background: 'linear-gradient(to bottom, rgba(0,0,0,0.8), transparent)', 
         zIndex: 10,
         pointerEvents: 'none' // Let clicks pass through to map where possible, but buttons need pointer-events: auto
       }}>
         <span className="command-panel-title" style={{ pointerEvents: 'auto' }}>World State</span>
         {onExpand && (
           <button 
              onClick={onExpand}
              style={{ 
                pointerEvents: 'auto',
                background: 'rgba(0, 255, 198, 0.1)', 
                border: '1px solid var(--color-accent-primary)', 
                color: 'var(--color-accent-primary)', 
                borderRadius: '4px',
                padding: '4px 8px',
                cursor: 'pointer',
                fontSize: '10px',
                fontFamily: 'var(--font-header)',
                textTransform: 'uppercase'
              }}
           >
             Expand ↗
           </button>
         )}
       </div>

       {/* Map takes full height of center column now */}
      <WorldStateMap loading={loading} error={error} />
    </Box>
  );
});

WorldPanel.displayName = 'WorldPanel';

export default WorldPanel;

