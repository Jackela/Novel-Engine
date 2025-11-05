import React, { useState, useRef } from 'react';
import { logger } from '../../services/logging/LoggerFactory';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Paper,
  IconButton,
  Tooltip,
  Chip,
  Divider,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Fab,
  Menu,
  MenuItem,
  ListItemIcon,
} from '@mui/material';
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  Print as PrintIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  FormatSize as FormatSizeIcon,
  MoreVert as MoreVertIcon,
  AutoStories as StoryIcon,
  Schedule as ScheduleIcon,
  Group as GroupIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import type { StoryProject } from '../../types';
import { useFocusTrap } from '../../utils/focusManagement';

interface Props {
  story: StoryProject;
  onEdit: (updatedStory: StoryProject) => void;
}

export default function StoryDisplay({ story, onEdit }: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(story.storyContent || '');
  const [fontSize, setFontSize] = useState(16);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [showMetadata, setShowMetadata] = useState(false);
  
  // Focus management for metadata dialog
  const metadataDialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(showMetadata, metadataDialogRef, {
    onEscape: () => setShowMetadata(false),
    restoreFocus: true,
  });

  const handleStartEdit = () => {
    setEditedContent(story.storyContent || '');
    setIsEditing(true);
  };

  const handleSaveEdit = () => {
    const updatedStory = {
      ...story,
      storyContent: editedContent,
      updatedAt: new Date(),
    };
    onEdit(updatedStory);
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditedContent(story.storyContent || '');
    setIsEditing(false);
  };

  const handleCopyContent = async () => {
    try {
      await navigator.clipboard.writeText(story.storyContent || '');
      // TODO: Show success notification
    } catch (error) {
      logger.error('Failed to copy content:', error);
    }
    setMenuAnchor(null);
  };

  const handleExportText = () => {
    const blob = new Blob([story.storyContent || ''], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${story.title.replace(/[^a-z0-9]/gi, '_')}.txt`;
    link.click();
    URL.revokeObjectURL(url);
    setMenuAnchor(null);
  };

  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <html>
          <head>
            <title>${story.title}</title>
            <style>
              body { 
                font-family: 'Times New Roman', serif; 
                line-height: 1.6; 
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px; 
              }
              h1 { text-align: center; margin-bottom: 30px; }
              p { margin-bottom: 16px; }
            </style>
          </head>
          <body>
            <h1>${story.title}</h1>
            <div style="white-space: pre-wrap;">${story.storyContent}</div>
          </body>
        </html>
      `);
      printWindow.document.close();
      printWindow.print();
    }
    setMenuAnchor(null);
  };

  const formatDate = (date: Date | string | undefined) => {
    if (!date) return 'Unknown';
    const d = date instanceof Date ? date : new Date(date);
    return d.toLocaleString();
  };

  const getReadingTime = () => {
    const wordCount = story.metadata?.wordCount || 0;
    return Math.ceil(wordCount / 200); // ~200 words per minute
  };

  return (
    <Box>
      {/* Story Header */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h4" component="h1" sx={{ fontWeight: 700, mb: 1 }}>
                {story.title}
              </Typography>
              
              <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                {story.description}
              </Typography>

              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                <Chip
                  icon={<GroupIcon />}
                  label={`${story.characters?.length || 0} Characters`}
                  size="small"
                  variant="outlined"
                />
                <Chip
                  icon={<StoryIcon />}
                  label={`${story.metadata?.wordCount || 0} Words`}
                  size="small"
                  variant="outlined"
                />
                <Chip
                  icon={<ScheduleIcon />}
                  label={`${getReadingTime()} min read`}
                  size="small"
                  variant="outlined"
                />
                {story.metadata?.generationTime && (
                  <Chip
                    icon={<SpeedIcon />}
                    label={`Generated in ${story.metadata.generationTime}s`}
                    size="small"
                    variant="outlined"
                  />
                )}
                <Chip
                  label={story.status}
                  size="small"
                  color={story.status === 'completed' ? 'success' : 'primary'}
                />
              </Box>
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title="Adjust font size">
                <IconButton onClick={(e) => setMenuAnchor(e.currentTarget)}>
                  <FormatSizeIcon />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Show metadata">
                <IconButton onClick={() => setShowMetadata(true)}>
                  <MoreVertIcon />
                </IconButton>
              </Tooltip>
            </Box>

            <Menu
              anchorEl={menuAnchor}
              open={Boolean(menuAnchor)}
              onClose={() => setMenuAnchor(null)}
            >
              <MenuItem onClick={() => { setFontSize(Math.max(12, fontSize - 2)); setMenuAnchor(null); }}>
                <ListItemIcon><ZoomOutIcon /></ListItemIcon>
                Decrease font size
              </MenuItem>
              <MenuItem onClick={() => { setFontSize(Math.min(24, fontSize + 2)); setMenuAnchor(null); }}>
                <ListItemIcon><ZoomInIcon /></ListItemIcon>
                Increase font size
              </MenuItem>
              <Divider />
              <MenuItem onClick={handleCopyContent}>
                <ListItemIcon><CopyIcon /></ListItemIcon>
                Copy content
              </MenuItem>
              <MenuItem onClick={handleExportText}>
                <ListItemIcon><DownloadIcon /></ListItemIcon>
                Export as text
              </MenuItem>
              <MenuItem onClick={handlePrint}>
                <ListItemIcon><PrintIcon /></ListItemIcon>
                Print story
              </MenuItem>
            </Menu>
          </Box>

          {/* Character Participants */}
          {story.characters && story.characters.length > 0 && (
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                Story Participants
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {story.characters.map((character, _index) => (
                  <Chip
                    key={character}
                    avatar={<Avatar sx={{ width: 24, height: 24, fontSize: '0.75rem' }}>
                      {character.charAt(0).toUpperCase()}
                    </Avatar>}
                    label={character.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    variant="outlined"
                    size="small"
                  />
                ))}
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Story Content */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Story Content
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 1 }}>
              {!isEditing ? (
                <Button
                  startIcon={<EditIcon />}
                  onClick={handleStartEdit}
                  variant="outlined"
                  size="small"
                >
                  Edit
                </Button>
              ) : (
                <>
                  <Button
                    startIcon={<SaveIcon />}
                    onClick={handleSaveEdit}
                    variant="contained"
                    size="small"
                  >
                    Save
                  </Button>
                  <Button
                    startIcon={<CancelIcon />}
                    onClick={handleCancelEdit}
                    variant="outlined"
                    size="small"
                  >
                    Cancel
                  </Button>
                </>
              )}
            </Box>
          </Box>

          {isEditing ? (
            <TextField
              fullWidth
              multiline
              minRows={15}
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              placeholder="Enter your story content..."
              sx={{
                '& .MuiInputBase-input': {
                  fontSize: `${fontSize}px`,
                  lineHeight: 1.7,
                  fontFamily: '"Georgia", "Times New Roman", serif',
                },
              }}
            />
          ) : (
            <Paper
              sx={{
                p: 3,
                minHeight: 400,
                bgcolor: 'background.paper',
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              <Typography
                variant="body1"
                sx={{
                  fontSize: `${fontSize}px`,
                  lineHeight: 1.7,
                  fontFamily: '"Georgia", "Times New Roman", serif',
                  whiteSpace: 'pre-wrap',
                  color: 'text.primary',
                }}
              >
                {story.storyContent || 'No content available.'}
              </Typography>
            </Paper>
          )}
        </CardContent>
      </Card>

      {/* Floating Action Buttons */}
      <Box sx={{ position: 'fixed', bottom: 24, right: 24, display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Tooltip title="Copy to clipboard" placement="left">
          <Fab size="small" color="default" onClick={handleCopyContent}>
            <CopyIcon />
          </Fab>
        </Tooltip>
        
        <Tooltip title="Export story" placement="left">
          <Fab size="small" color="primary" onClick={handleExportText}>
            <DownloadIcon />
          </Fab>
        </Tooltip>
      </Box>

      {/* Story Metadata Dialog */}
      <Dialog
        open={showMetadata}
        onClose={() => setShowMetadata(false)}
        maxWidth="sm"
        fullWidth
        ref={metadataDialogRef}
        aria-labelledby="story-metadata-title"
        aria-describedby="story-metadata-description"
      >
        <DialogTitle>
          <Typography 
            variant="h6" 
            id="story-metadata-title"
            sx={{ fontWeight: 600 }}
          >
            Story Metadata
          </Typography>
        </DialogTitle>
        
        <DialogContent>
          <List id="story-metadata-description">
            <ListItem>
              <ListItemText
                primary="Story ID"
                secondary={story.id}
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary="Status"
                secondary={story.status}
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary="Created"
                secondary={formatDate(story.createdAt)}
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary="Last Modified"
                secondary={formatDate(story.updatedAt)}
              />
            </ListItem>
            {story.metadata && (
              <>
                <ListItem>
                  <ListItemText
                    primary="Word Count"
                    secondary={story.metadata.wordCount?.toLocaleString() || 'Unknown'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Generation Time"
                    secondary={story.metadata.generationTime ? `${story.metadata.generationTime} seconds` : 'Unknown'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Total Turns"
                    secondary={story.metadata.totalTurns || 'Unknown'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Participant Count"
                    secondary={story.metadata.participantCount || 'Unknown'}
                  />
                </ListItem>
              </>
            )}
          </List>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setShowMetadata(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

