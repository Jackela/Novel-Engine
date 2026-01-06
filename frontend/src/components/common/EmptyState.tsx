import React from 'react';
import { Box, Typography, Button, useTheme } from '@mui/material';
import { motion } from 'framer-motion';
import AddIcon from '@mui/icons-material/Add';

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

const EmptyStateIcon: React.FC<{ icon: React.ReactNode }> = ({ icon }) => {
  const theme = useTheme();
  return (
    <Box
      component={motion.div}
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ delay: 0.2, duration: 0.5 }}
      sx={{
        mb: 3,
        color: theme.palette.text.secondary,
        '& svg': { fontSize: 64 },
      }}
    >
      {icon}
    </Box>
  );
};

const EmptyStateTitle: React.FC<{ title: string }> = ({ title }) => {
  const theme = useTheme();
  return (
    <Typography
      variant="h4"
      component={motion.h4}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.3 }}
      sx={{ 
        mb: 2, 
        fontWeight: 600,
        background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
        backgroundClip: 'text',
        textFillColor: 'transparent',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
      }}
    >
      {title}
    </Typography>
  );
};

const EmptyStateDescription: React.FC<{ description: string }> = ({ description }) => (
  <Typography
    variant="body1"
    color="text.secondary"
    component={motion.p}
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ delay: 0.4 }}
    sx={{ mb: 4, maxWidth: '500px' }}
  >
    {description}
  </Typography>
);

const EmptyStateAction: React.FC<{ label: string; onAction: () => void }> = ({ label, onAction }) => {
  const theme = useTheme();
  return (
    <Button
      component={motion.button}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      variant="contained"
      size="large"
      startIcon={<AddIcon />}
      onClick={onAction}
      sx={{
        px: 4,
        py: 1.5,
        borderRadius: 2,
        fontSize: '1.1rem',
        textTransform: 'none',
        boxShadow: `0 8px 16px ${theme.palette.primary.main}40`,
      }}
    >
      {label}
    </Button>
  );
};

const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  icon,
}) => {
  const theme = useTheme();

  return (
    <Box
      component={motion.div}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        minHeight: '400px',
        p: 4,
        textAlign: 'center',
        background: `radial-gradient(circle at center, ${theme.palette.action.hover} 0%, transparent 70%)`,
        borderRadius: 4,
        border: `1px dashed ${theme.palette.divider}`,
      }}
    >
      {icon && <EmptyStateIcon icon={icon} />}
      <EmptyStateTitle title={title} />
      <EmptyStateDescription description={description} />
      {actionLabel && onAction && (
        <EmptyStateAction label={actionLabel} onAction={onAction} />
      )}
    </Box>
  );
};

export default EmptyState;
