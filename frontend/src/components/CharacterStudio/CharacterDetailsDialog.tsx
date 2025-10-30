import React, { useState, useMemo, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Avatar,
  Chip,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  LinearProgress,
  Alert,
  Tabs,
  Tab,
  Paper,
  Tooltip,
  Divider,
  Menu,
  MenuItem,
  ListItemSecondaryAction,
} from '@mui/material';
import {
  Close as CloseIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  ContentCopy as CopyIcon,
  MoreVert as MoreVertIcon,
  Shield as ShieldIcon,
  Sword as SwordIcon,
  Build as BuildIcon,
  Psychology as PsychologyIcon,
  Visibility as VisibilityIcon,
  Forum as ForumIcon,
  Star as StarIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import type { Character } from '../../types';
import { useFocusTrap } from '../../utils/focusManagement';

interface Props {
  open: boolean;
  onClose: () => void;
  character: Character | null;
  characterName: string | null;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`character-tabpanel-${index}`}
      aria-labelledby={`character-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
}

const StatIcons = {
  strength: ShieldIcon,
  dexterity: TimelineIcon,
  intelligence: PsychologyIcon,
  willpower: StarIcon,
  perception: VisibilityIcon,
  charisma: ForumIcon,
};

export default function CharacterDetailsDialog({ 
  open, 
  onClose, 
  character, 
  characterName 
}: Props) {
  const [activeTab, setActiveTab] = useState(0);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  
  // Focus management for accessibility
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, dialogRef, {
    onEscape: onClose,
    restoreFocus: true,
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleEdit = () => {
    handleMenuClose();
    // TODO: Implement edit functionality
    console.log('Edit character:', characterName);
  };

  const handleDelete = () => {
    handleMenuClose();
    // TODO: Implement delete functionality with confirmation
    console.log('Delete character:', characterName);
  };

  const handleExport = () => {
    handleMenuClose();
    if (character) {
      // Export character data as JSON
      const dataStr = JSON.stringify(character, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${character.name}_character.json`;
      link.click();
      URL.revokeObjectURL(url);
    }
  };

  const handleCopyData = async () => {
    handleMenuClose();
    if (character) {
      try {
        await navigator.clipboard.writeText(JSON.stringify(character, null, 2));
        // TODO: Show success notification
      } catch (error) {
        console.error('Failed to copy character data:', error);
      }
    }
  };

  // Calculate character statistics
  const characterStats = useMemo(() => {
    if (!character) return null;

    const totalStats = Object.values(character.stats).reduce((sum, val) => sum + val, 0);
    const avgStat = totalStats / Object.keys(character.stats).length;
    const equipmentCount = character.equipment?.length || 0;
    const relationshipCount = character.relationships?.length || 0;

    // Calculate equipment condition average
    const avgCondition = character.equipment?.length 
      ? character.equipment.reduce((sum, eq) => sum + eq.condition, 0) / character.equipment.length
      : 0;

    return {
      totalStats,
      avgStat: Math.round(avgStat * 10) / 10,
      equipmentCount,
      relationshipCount,
      avgCondition: Math.round(avgCondition * 100),
      wordCount: character.description?.split(' ').length || 0,
    };
  }, [character]);

  const getStatColor = (value: number) => {
    if (value >= 8) return 'success';
    if (value >= 6) return 'info';
    if (value >= 4) return 'warning';
    return 'error';
  };

  const getFactionColor = (faction: string) => {
    const colors: Record<string, string> = {
      'Alliance Network': 'var(--color-character-protagonist)',
      'Entropy Cult': 'var(--color-character-antagonist)',
      'Freewind Collective': 'var(--color-character-supporting)',
      'Bastion Cohort': 'var(--color-character-neutral)',
      'Starborne Conclave': 'var(--color-arc-mystery)',
      'Harmonic Assembly': 'var(--color-event-emotional)',
      'Synthetic Vanguard': 'var(--color-info)',
      'Adaptive Swarm': 'var(--color-secondary)',
      'Other': 'var(--color-text-tertiary)',
    };
    return colors[faction] || 'var(--color-text-tertiary)';
  };

  if (!character) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogContent sx={{ textAlign: 'center', py: 4 }}>
          <Alert severity="error">
            Character not found or failed to load.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>
    );
  }

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="lg" 
      fullWidth
      ref={dialogRef}
      aria-labelledby="character-details-title"
      aria-describedby="character-details-description"
      PaperProps={{
        sx: { minHeight: '80vh', maxHeight: '90vh' }
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar
            sx={{
              width: 56,
              height: 56,
              bgcolor: getFactionColor(character.faction),
              fontSize: '1.5rem',
              fontWeight: 700,
            }}
          >
            {character.name.charAt(0).toUpperCase()}
          </Avatar>
          
          <Box sx={{ flexGrow: 1 }}>
            <Typography 
              variant="h4" 
              component="div" 
              id="character-details-title"
              sx={{ fontWeight: 700, mb: 0.5 }}
            >
              {character.name}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip
                label={character.faction}
                sx={{
                  bgcolor: getFactionColor(character.faction),
                  color: 'white',
                  fontWeight: 600,
                }}
              />
              <Chip
                label={character.role}
                variant="outlined"
                color="primary"
              />
              {characterStats && (
                <Chip
                  label={`${characterStats.totalStats} Total Stats`}
                  variant="outlined"
                  size="small"
                />
              )}
            </Box>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Tooltip title="More actions">
              <IconButton onClick={handleMenuOpen}>
                <MoreVertIcon />
              </IconButton>
            </Tooltip>
            <IconButton onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>

        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={handleMenuClose}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        >
          <MenuItem onClick={handleEdit}>
            <ListItemIcon><EditIcon fontSize="small" /></ListItemIcon>
            <ListItemText>Edit Character</ListItemText>
          </MenuItem>
          <MenuItem onClick={handleExport}>
            <ListItemIcon><DownloadIcon fontSize="small" /></ListItemIcon>
            <ListItemText>Export Data</ListItemText>
          </MenuItem>
          <MenuItem onClick={handleCopyData}>
            <ListItemIcon><CopyIcon fontSize="small" /></ListItemIcon>
            <ListItemText>Copy Data</ListItemText>
          </MenuItem>
          <Divider />
          <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
            <ListItemIcon><DeleteIcon fontSize="small" color="error" /></ListItemIcon>
            <ListItemText>Delete Character</ListItemText>
          </MenuItem>
        </Menu>
      </DialogTitle>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="character details tabs">
          <Tab label="Overview" />
          <Tab label="Stats & Equipment" />
          <Tab label="Relationships" />
          <Tab label="History" />
        </Tabs>
      </Box>

      <DialogContent sx={{ px: 0, pt: 0 }}>
        {/* Overview Tab */}
        <TabPanel value={activeTab} index={0}>
          <Box sx={{ px: 3 }}>
            <Grid container spacing={3}>
              {/* Character Description */}
              <Grid item xs={12} md={8}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                      Character Description
                    </Typography>
                    <Typography 
                      variant="body1" 
                      id="character-details-description"
                      sx={{ lineHeight: 1.7, whiteSpace: 'pre-wrap' }}
                    >
                      {character.description}
                    </Typography>
                    {characterStats && (
                      <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
                        <Typography variant="caption" color="text.secondary">
                          {characterStats.wordCount} words • Created {character.createdAt ? new Date(character.createdAt).toLocaleDateString() : 'Unknown'}
                        </Typography>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>

              {/* Quick Stats */}
              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                      Quick Stats
                    </Typography>
                    
                    {characterStats && (
                      <List dense>
                        <ListItem>
                          <ListItemText 
                            primary="Total Stats" 
                            secondary={`${characterStats.totalStats} points`}
                          />
                        </ListItem>
                        <ListItem>
                          <ListItemText 
                            primary="Average Stat" 
                            secondary={`${characterStats.avgStat}/10`}
                          />
                        </ListItem>
                        <ListItem>
                          <ListItemText 
                            primary="Equipment" 
                            secondary={`${characterStats.equipmentCount} items`}
                          />
                        </ListItem>
                        <ListItem>
                          <ListItemText 
                            primary="Equipment Condition" 
                            secondary={`${characterStats.avgCondition}% average`}
                          />
                        </ListItem>
                        <ListItem>
                          <ListItemText 
                            primary="Relationships" 
                            secondary={`${characterStats.relationshipCount} connections`}
                          />
                        </ListItem>
                      </List>
                    )}
                  </CardContent>
                </Card>

                {/* Character Metadata */}
                <Card sx={{ mt: 2 }}>
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                      Metadata
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemText 
                          primary="Created" 
                          secondary={character.createdAt ? new Date(character.createdAt).toLocaleString() : 'Unknown'}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText 
                          primary="Last Modified" 
                          secondary={character.updatedAt ? new Date(character.updatedAt).toLocaleString() : 'Unknown'}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText 
                          primary="Character ID" 
                          secondary={character.id}
                        />
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        </TabPanel>

        {/* Stats & Equipment Tab */}
        <TabPanel value={activeTab} index={1}>
          <Box sx={{ px: 3 }}>
            <Grid container spacing={3}>
              {/* Character Stats */}
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                      Character Statistics
                    </Typography>
                    
                    <Grid container spacing={2}>
                      {Object.entries(character.stats).map(([stat, value]) => {
                        const IconComponent = StatIcons[stat as keyof typeof StatIcons];
                        return (
                          <Grid item xs={12} key={stat}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                              <IconComponent sx={{ color: 'text.secondary' }} />
                              <Box sx={{ flexGrow: 1 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                    {stat.charAt(0).toUpperCase() + stat.slice(1)}
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {value}/10
                                  </Typography>
                                </Box>
                                <LinearProgress
                                  variant="determinate"
                                  value={(value / 10) * 100}
                                  color={getStatColor(value)}
                                  sx={{ height: 8, borderRadius: 1 }}
                                />
                              </Box>
                            </Box>
                          </Grid>
                        );
                      })}
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>

              {/* Equipment */}
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                      Equipment ({character.equipment?.length || 0})
                    </Typography>
                    
                    {character.equipment && character.equipment.length > 0 ? (
                      <List dense>
                        {character.equipment.map((item, index) => (
                          <ListItem key={item.id || index} divider={index < character.equipment!.length - 1}>
                            <ListItemIcon>
                              {item.type === 'weapon' ? <SwordIcon /> : 
                               item.type === 'armor' ? <ShieldIcon /> : <BuildIcon />}
                            </ListItemIcon>
                            <ListItemText
                              primary={
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                    {item.name}
                                  </Typography>
                                  <Chip 
                                    label={item.type} 
                                    size="small" 
                                    variant="outlined"
                                  />
                                </Box>
                              }
                              secondary={
                                <Box>
                                  <Typography variant="body2" color="text.secondary">
                                    {item.description || 'No description'}
                                  </Typography>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                                    <Typography variant="caption">Condition:</Typography>
                                    <LinearProgress
                                      variant="determinate"
                                      value={item.condition * 100}
                                      color={item.condition > 0.7 ? 'success' : item.condition > 0.3 ? 'warning' : 'error'}
                                      sx={{ flexGrow: 1, height: 4, borderRadius: 1 }}
                                    />
                                    <Typography variant="caption">
                                      {Math.round(item.condition * 100)}%
                                    </Typography>
                                  </Box>
                                </Box>
                              }
                            />
                          </ListItem>
                        ))}
                      </List>
                    ) : (
                      <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'action.hover' }}>
                        <BuildIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                        <Typography variant="body2" color="text.secondary">
                          No equipment assigned to this character
                        </Typography>
                      </Paper>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        </TabPanel>

        {/* Relationships Tab */}
        <TabPanel value={activeTab} index={2}>
          <Box sx={{ px: 3 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                  Character Relationships
                </Typography>
                
                {character.relationships && character.relationships.length > 0 ? (
                  <List>
                    {character.relationships.map((relationship, index) => (
                      <ListItem key={index} divider={index < character.relationships!.length - 1}>
                        <ListItemText
                          primary={relationship.targetCharacterId}
                          secondary={
                            <Box>
                              <Typography variant="body2" color="text.secondary">
                                Type: {relationship.type}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {relationship.description}
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Paper sx={{ p: 4, textAlign: 'center', bgcolor: 'action.hover' }}>
                    <ForumIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                      No Relationships
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      This character hasn't formed any relationships yet.
                    </Typography>
                  </Paper>
                )}
              </CardContent>
            </Card>
          </Box>
        </TabPanel>

        {/* History Tab */}
        <TabPanel value={activeTab} index={3}>
          <Box sx={{ px: 3 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                  Character History
                </Typography>
                
                <Paper sx={{ p: 4, textAlign: 'center', bgcolor: 'action.hover' }}>
                  <TimelineIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                    History Tracking
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Character modification history and story participation will be displayed here.
                  </Typography>
                </Paper>
              </CardContent>
            </Card>
          </Box>
        </TabPanel>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={onClose} size="large">
          Close
        </Button>
        <Button 
          variant="outlined" 
          startIcon={<EditIcon />}
          onClick={handleEdit}
          size="large"
        >
          Edit Character
        </Button>
        <Button 
          variant="contained" 
          startIcon={<ShareIcon />}
          onClick={handleExport}
          size="large"
        >
          Export
        </Button>
      </DialogActions>
    </Dialog>
  );
}
