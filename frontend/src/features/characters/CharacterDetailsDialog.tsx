import React, { useState, useMemo, useRef } from 'react';
import { logger } from '@/services/logging/LoggerFactory';
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
  Gavel as SwordIcon,
  Build as BuildIcon,
  Psychology as PsychologyIcon,
  Visibility as VisibilityIcon,
  Forum as ForumIcon,
  Star as StarIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import type { Character } from '@/types';
import { useFocusTrap } from '@/utils/focusManagement';

interface Props {
  open: boolean;
  onClose: () => void;
  character: Character | null;
  characterName: string | null;
  onEdit?: () => void;
  onDelete?: () => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

interface CharacterStatsSummary {
  totalStats: number;
  avgStat: number;
  equipmentCount: number;
  relationshipCount: number;
  avgCondition: number;
  wordCount: number;
}

const STAT_ICONS = {
  strength: ShieldIcon,
  dexterity: TimelineIcon,
  intelligence: PsychologyIcon,
  willpower: StarIcon,
  perception: VisibilityIcon,
  charisma: ForumIcon,
};

const FACTION_COLORS: Record<string, string> = {
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

const getStatColor = (value: number) => {
  if (value >= 8) return 'success';
  if (value >= 6) return 'info';
  if (value >= 4) return 'warning';
  return 'error';
};

const getFactionColor = (faction: string) =>
  FACTION_COLORS[faction] || 'var(--color-text-tertiary)';

const buildCharacterStats = (character: Character | null): CharacterStatsSummary | null => {
  if (!character) return null;

  const totalStats = Object.values(character.stats).reduce((sum, val) => sum + val, 0);
  const avgStat = totalStats / Object.keys(character.stats).length;
  const equipmentCount = character.equipment?.length || 0;
  const relationshipCount = character.relationships?.length || 0;
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
};

const exportCharacterData = (character: Character) => {
  const dataStr = JSON.stringify(character, null, 2);
  const dataBlob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(dataBlob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${character.name}_character.json`;
  link.click();
  URL.revokeObjectURL(url);
};

const copyCharacterData = async (character: Character) => {
  await navigator.clipboard.writeText(JSON.stringify(character, null, 2));
};

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

const CharacterDetailsHeader: React.FC<{
  character: Character;
  characterStats: CharacterStatsSummary | null;
  onMenuOpen: (event: React.MouseEvent<HTMLElement>) => void;
  onClose: () => void;
}> = ({ character, characterStats, onMenuOpen, onClose }) => (
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
          <Chip label={character.role} variant="outlined" color="primary" />
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
          <IconButton onClick={onMenuOpen}>
            <MoreVertIcon />
          </IconButton>
        </Tooltip>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </Box>
    </Box>
  </DialogTitle>
);

const CharacterDetailsMenu: React.FC<{
  anchorEl: HTMLElement | null;
  onClose: () => void;
  onEdit: () => void;
  onExport: () => void;
  onCopyData: () => void;
  onDelete: () => void;
}> = ({ anchorEl, onClose, onEdit, onExport, onCopyData, onDelete }) => (
  <Menu
    anchorEl={anchorEl}
    open={Boolean(anchorEl)}
    onClose={onClose}
    anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
    transformOrigin={{ vertical: 'top', horizontal: 'right' }}
  >
    <MenuItem onClick={onEdit}>
      <ListItemIcon>
        <EditIcon fontSize="small" />
      </ListItemIcon>
      <ListItemText>Edit Character</ListItemText>
    </MenuItem>
    <MenuItem onClick={onExport}>
      <ListItemIcon>
        <DownloadIcon fontSize="small" />
      </ListItemIcon>
      <ListItemText>Export Data</ListItemText>
    </MenuItem>
    <MenuItem onClick={onCopyData}>
      <ListItemIcon>
        <CopyIcon fontSize="small" />
      </ListItemIcon>
      <ListItemText>Copy Data</ListItemText>
    </MenuItem>
    <Divider />
    <MenuItem onClick={onDelete} sx={{ color: 'error.main' }}>
      <ListItemIcon>
        <DeleteIcon fontSize="small" color="error" />
      </ListItemIcon>
      <ListItemText>Delete Character</ListItemText>
    </MenuItem>
  </Menu>
);

const CharacterDescriptionCard: React.FC<{
  character: Character;
  characterStats: CharacterStatsSummary | null;
}> = ({ character, characterStats }) => (
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
            {characterStats.wordCount} words • Created{' '}
            {character.createdAt ? new Date(character.createdAt).toLocaleDateString() : 'Unknown'}
          </Typography>
        </Box>
      )}
    </CardContent>
  </Card>
);

const CharacterQuickStatsCard: React.FC<{
  characterStats: CharacterStatsSummary | null;
}> = ({ characterStats }) => (
  <Card>
    <CardContent>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Quick Stats
      </Typography>

      {characterStats && (
        <List dense>
          <ListItem>
            <ListItemText primary="Total Stats" secondary={`${characterStats.totalStats} points`} />
          </ListItem>
          <ListItem>
            <ListItemText primary="Average Stat" secondary={`${characterStats.avgStat}/10`} />
          </ListItem>
          <ListItem>
            <ListItemText primary="Equipment" secondary={`${characterStats.equipmentCount} items`} />
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
);

const CharacterMetadataCard: React.FC<{ character: Character }> = ({ character }) => (
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
          <ListItemText primary="Character ID" secondary={character.id} />
        </ListItem>
      </List>
    </CardContent>
  </Card>
);

const CharacterOverviewTab: React.FC<{
  character: Character;
  characterStats: CharacterStatsSummary | null;
}> = ({ character, characterStats }) => (
  <Box sx={{ px: 3 }}>
    <Grid container spacing={3}>
      <Grid item xs={12} md={8}>
        <CharacterDescriptionCard character={character} characterStats={characterStats} />
      </Grid>
      <Grid item xs={12} md={4}>
        <CharacterQuickStatsCard characterStats={characterStats} />
        <CharacterMetadataCard character={character} />
      </Grid>
    </Grid>
  </Box>
);

const CharacterStatsCard: React.FC<{ stats: Character['stats'] }> = ({ stats }) => (
  <Card>
    <CardContent>
      <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
        Character Statistics
      </Typography>

      <Grid container spacing={2}>
        {Object.entries(stats).map(([stat, value]) => {
          const IconComponent = STAT_ICONS[stat as keyof typeof STAT_ICONS];
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
);

const getEquipmentIcon = (type: string) => {
  if (type === 'weapon') return <SwordIcon />;
  if (type === 'armor') return <ShieldIcon />;
  return <BuildIcon />;
};

const CharacterEquipmentCard: React.FC<{ equipment: Character['equipment'] }> = ({ equipment }) => (
  <Card>
    <CardContent>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Equipment ({equipment?.length || 0})
      </Typography>

      {equipment && equipment.length > 0 ? (
        <List dense>
          {equipment.map((item, index) => (
            <ListItem key={item.id || index} divider={index < equipment.length - 1}>
              <ListItemIcon>{getEquipmentIcon(item.type)}</ListItemIcon>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      {item.name}
                    </Typography>
                    <Chip label={item.type} size="small" variant="outlined" />
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
);

const CharacterStatsEquipmentTab: React.FC<{ character: Character }> = ({ character }) => (
  <Box sx={{ px: 3 }}>
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <CharacterStatsCard stats={character.stats} />
      </Grid>
      <Grid item xs={12} md={6}>
        <CharacterEquipmentCard equipment={character.equipment} />
      </Grid>
    </Grid>
  </Box>
);

const CharacterRelationshipsTab: React.FC<{ character: Character }> = ({ character }) => (
  <Box sx={{ px: 3 }}>
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Character Relationships
        </Typography>

        {character.relationships && character.relationships.length > 0 ? (
          <List>
            {character.relationships.map((relationship, index) => (
              <ListItem key={index} divider={index < character.relationships.length - 1}>
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
);

const CharacterHistoryTab: React.FC = () => (
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
);

const CharacterNotFoundDialog: React.FC<{
  open: boolean;
  onClose: () => void;
}> = ({ open, onClose }) => (
  <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
    <DialogContent sx={{ textAlign: 'center', py: 4 }}>
      <Alert severity="error">Character not found or failed to load.</Alert>
    </DialogContent>
    <DialogActions>
      <Button onClick={onClose}>Close</Button>
    </DialogActions>
  </Dialog>
);

const useCharacterDetailsDialogState = (params: Props) => {
  const { open, onClose, character, characterName, onEdit, onDelete } = params;
  const [activeTab, setActiveTab] = useState(0);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);

  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, dialogRef, {
    onEscape: onClose,
    restoreFocus: true,
  });

  const characterStats = useMemo(() => buildCharacterStats(character), [character]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
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
    if (onEdit) {
      onEdit();
      return;
    }
    logger.info('Edit character:', characterName);
  };

  const handleDelete = () => {
    handleMenuClose();
    if (onDelete) {
      onDelete();
      return;
    }
    logger.info('Delete character:', characterName);
  };

  const handleExport = () => {
    handleMenuClose();
    if (!character) return;
    exportCharacterData(character);
  };

  const handleCopyData = async () => {
    handleMenuClose();
    if (!character) return;
    try {
      await copyCharacterData(character);
    } catch (error) {
      logger.error('Failed to copy character data:', error);
    }
  };

  return {
    dialogRef,
    activeTab,
    menuAnchor,
    characterStats,
    handleTabChange,
    handleMenuOpen,
    handleMenuClose,
    handleEdit,
    handleDelete,
    handleExport,
    handleCopyData,
  };
};

const CharacterDetailsDialogView: React.FC<{
  open: boolean;
  onClose: () => void;
  character: Character;
  activeTab: number;
  onTabChange: (event: React.SyntheticEvent, newValue: number) => void;
  dialogRef: React.RefObject<HTMLDivElement>;
  menuAnchor: HTMLElement | null;
  characterStats: CharacterStatsSummary | null;
  onMenuOpen: (event: React.MouseEvent<HTMLElement>) => void;
  onMenuClose: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onExport: () => void;
  onCopyData: () => void;
}> = ({
  open,
  onClose,
  character,
  activeTab,
  onTabChange,
  dialogRef,
  menuAnchor,
  characterStats,
  onMenuOpen,
  onMenuClose,
  onEdit,
  onDelete,
  onExport,
  onCopyData,
}) => (
  <Dialog
    open={open}
    onClose={onClose}
    maxWidth="lg"
    fullWidth
    ref={dialogRef}
    aria-labelledby="character-details-title"
    aria-describedby="character-details-description"
    PaperProps={{
      sx: { minHeight: '80vh', maxHeight: '90vh' },
    }}
  >
    <CharacterDetailsHeader
      character={character}
      characterStats={characterStats}
      onMenuOpen={onMenuOpen}
      onClose={onClose}
    />
    <CharacterDetailsMenu
      anchorEl={menuAnchor}
      onClose={onMenuClose}
      onEdit={onEdit}
      onExport={onExport}
      onCopyData={onCopyData}
      onDelete={onDelete}
    />

    <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
      <Tabs value={activeTab} onChange={onTabChange} aria-label="character details tabs">
        <Tab label="Overview" />
        <Tab label="Stats & Equipment" />
        <Tab label="Relationships" />
        <Tab label="History" />
      </Tabs>
    </Box>

    <DialogContent sx={{ px: 0, pt: 0 }}>
      <TabPanel value={activeTab} index={0}>
        <CharacterOverviewTab character={character} characterStats={characterStats} />
      </TabPanel>
      <TabPanel value={activeTab} index={1}>
        <CharacterStatsEquipmentTab character={character} />
      </TabPanel>
      <TabPanel value={activeTab} index={2}>
        <CharacterRelationshipsTab character={character} />
      </TabPanel>
      <TabPanel value={activeTab} index={3}>
        <CharacterHistoryTab />
      </TabPanel>
    </DialogContent>

    <DialogActions sx={{ px: 3, pb: 3 }}>
      <Button onClick={onClose} size="large">
        Close
      </Button>
      <Button variant="outlined" startIcon={<EditIcon />} onClick={onEdit} size="large">
        Edit Character
      </Button>
      <Button variant="contained" startIcon={<ShareIcon />} onClick={onExport} size="large">
        Export
      </Button>
    </DialogActions>
  </Dialog>
);

export default function CharacterDetailsDialog(props: Props) {
  const {
    dialogRef,
    activeTab,
    menuAnchor,
    characterStats,
    handleTabChange,
    handleMenuOpen,
    handleMenuClose,
    handleEdit,
    handleDelete,
    handleExport,
    handleCopyData,
  } = useCharacterDetailsDialogState(props);

  if (!props.character) {
    return <CharacterNotFoundDialog open={props.open} onClose={props.onClose} />;
  }

  return (
    <CharacterDetailsDialogView
      open={props.open}
      onClose={props.onClose}
      character={props.character}
      activeTab={activeTab}
      onTabChange={handleTabChange}
      dialogRef={dialogRef}
      menuAnchor={menuAnchor}
      characterStats={characterStats}
      onMenuOpen={handleMenuOpen}
      onMenuClose={handleMenuClose}
      onEdit={handleEdit}
      onDelete={handleDelete}
      onExport={handleExport}
      onCopyData={handleCopyData}
    />
  );
}
