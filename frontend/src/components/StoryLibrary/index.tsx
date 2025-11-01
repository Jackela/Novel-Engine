import React, { useState, useMemo } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Avatar,
  IconButton,
  Menu,
  Tooltip,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemSecondaryAction,
  Divider,
  Alert,
  Skeleton,
  Pagination,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Sort as SortIcon,
  ViewModule as GridViewIcon,
  ViewList as ListViewIcon,
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  Visibility as ViewIcon,
  AutoStories as StoryIcon,
  Group as GroupIcon,
  Schedule as ScheduleIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
} from '@mui/icons-material';
import type { StoryProject } from '../../types';

// Mock data for stories - in real app, this would come from API
const MOCK_STORIES: StoryProject[] = [
  {
    id: 'story_1',
    title: 'The Last Stand of Cadia',
    description: 'A heroic tale of Alliance Network Guards defending against Entropy forces',
    characters: ['bastion_guardian', 'freewind_captain'],
    settings: {
      turns: 5,
      narrativeStyle: 'action',
      tone: 'heroic',
      perspective: 'third_person',
      maxWordsPerTurn: 200,
      scenario: 'Final battle on Cadia',
    },
    status: 'completed',
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
    updatedAt: new Date(Date.now() - 1 * 60 * 60 * 1000), // 1 hour ago
    storyContent: 'The battlefield stretched endlessly before them...',
    metadata: {
      totalTurns: 5,
      generationTime: 45.2,
      wordCount: 1247,
      participantCount: 2,
      tags: ['action', 'Novel Engine', 'heroic'],
    },
  },
  {
    id: 'story_2',
    title: 'Shadows in the Underhive',
    description: 'A dark investigation in the depths of a hive city',
    characters: ['isabella_varr'],
    settings: {
      turns: 8,
      narrativeStyle: 'descriptive',
      tone: 'dark',
      perspective: 'first_person',
      maxWordsPerTurn: 300,
      scenario: 'Investigating mysterious disappearances',
    },
    status: 'completed',
    createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
    updatedAt: new Date(Date.now() - 23 * 60 * 60 * 1000), // 23 hours ago
    storyContent: 'The darkness of the underhive pressed in around me...',
    metadata: {
      totalTurns: 8,
      generationTime: 78.5,
      wordCount: 2156,
      participantCount: 1,
      tags: ['mystery', 'dark', 'investigation'],
    },
  },
  {
    id: 'story_3',
    title: 'Brothers in Arms',
    description: 'A tale of camaraderie between unlikely allies',
    characters: ['bastion_guardian', 'test_character'],
    settings: {
      turns: 6,
      narrativeStyle: 'dialogue',
      tone: 'neutral',
      perspective: 'third_person',
      maxWordsPerTurn: 250,
      scenario: 'Two soldiers from different worlds forced to work together',
    },
    status: 'draft',
    createdAt: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
    updatedAt: new Date(Date.now() - 15 * 60 * 1000), // 15 minutes ago
    storyContent: 'The unlikely pair stood at the crossroads...',
    metadata: {
      totalTurns: 6,
      generationTime: 52.1,
      wordCount: 1543,
      participantCount: 2,
      tags: ['friendship', 'dialogue', 'character-study'],
    },
  },
];

type ViewMode = 'grid' | 'list';
type SortOption = 'newest' | 'oldest' | 'title' | 'wordCount';

interface StoryCardProps {
  story: StoryProject;
  viewMode: ViewMode;
  onView: (story: StoryProject) => void;
  onEdit: (story: StoryProject) => void;
  onDelete: (story: StoryProject) => void;
  onDownload: (story: StoryProject) => void;
}

const StoryCard: React.FC<StoryCardProps> = ({
  story,
  viewMode,
  onView,
  onEdit,
  onDelete,
  onDownload,
}) => {
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [isFavorited, setIsFavorited] = useState(false);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const formatDate = (date: Date | string) => {
    const d = date instanceof Date ? date : new Date(date);
    return d.toLocaleDateString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'draft':
        return 'warning';
      case 'generating':
        return 'info';
      default:
        return 'default';
    }
  };

  const getReadingTime = () => {
    const wordCount = story.metadata?.wordCount || 0;
    return Math.ceil(wordCount / 200); // ~200 words per minute
  };

  if (viewMode === 'list') {
    return (
      <Card sx={{ mb: 1 }}>
        <ListItem
          button
          onClick={() => onView(story)}
          sx={{ py: 2 }}
        >
          <ListItemAvatar>
            <Avatar sx={{ bgcolor: 'primary.main' }}>
              <StoryIcon />
            </Avatar>
          </ListItemAvatar>
          
          <ListItemText
            primary={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
                  {story.title}
                </Typography>
                <Chip
                  label={story.status}
                  size="small"
                  color={getStatusColor(story.status)}
                  variant="outlined"
                />
              </Box>
            }
            secondary={
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {story.description}
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                  <Typography variant="caption" color="text.secondary">
                    {story.metadata?.wordCount || 0} words
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {story.characters?.length || 0} characters
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {getReadingTime()} min read
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatDate(story.createdAt)}
                  </Typography>
                </Box>
              </Box>
            }
          />
          
          <ListItemSecondaryAction>
            <IconButton onClick={handleMenuOpen}>
              <MoreVertIcon />
            </IconButton>
          </ListItemSecondaryAction>
        </ListItem>

        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={handleMenuClose}
        >
          <MenuItem onClick={() => { onView(story); handleMenuClose(); }}>
            <ViewIcon sx={{ mr: 1 }} />
            View Story
          </MenuItem>
          <MenuItem onClick={() => { onEdit(story); handleMenuClose(); }}>
            <EditIcon sx={{ mr: 1 }} />
            Edit
          </MenuItem>
          <MenuItem onClick={() => { onDownload(story); handleMenuClose(); }}>
            <DownloadIcon sx={{ mr: 1 }} />
            Download
          </MenuItem>
          <Divider />
          <MenuItem onClick={() => { onDelete(story); handleMenuClose(); }} sx={{ color: 'error.main' }}>
            <DeleteIcon sx={{ mr: 1 }} />
            Delete
          </MenuItem>
        </Menu>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.2s ease-in-out',
        cursor: 'pointer',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: (theme) => theme.shadows[8],
        },
      }}
      onClick={() => onView(story)}
    >
      <CardContent sx={{ flexGrow: 1, pb: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Typography variant="h6" component="div" sx={{ fontWeight: 600, flexGrow: 1 }}>
            {story.title}
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                setIsFavorited(!isFavorited);
              }}
            >
              {isFavorited ? <StarIcon color="warning" /> : <StarBorderIcon />}
            </IconButton>
            <IconButton size="small" onClick={handleMenuOpen}>
              <MoreVertIcon />
            </IconButton>
          </Box>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, lineHeight: 1.5 }}>
          {story.description}
        </Typography>

        <Box sx={{ mb: 2 }}>
          <Chip
            label={story.status}
            size="small"
            color={getStatusColor(story.status)}
            variant="outlined"
            sx={{ mr: 1, mb: 1 }}
          />
          {story.metadata?.tags?.map((tag) => (
            <Chip
              key={tag}
              label={tag}
              size="small"
              variant="outlined"
              sx={{ mr: 1, mb: 1 }}
            />
          ))}
        </Box>

        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          {story.characters?.slice(0, 3).map((character) => (
            <Chip
              key={character}
              avatar={<Avatar sx={{ width: 20, height: 20, fontSize: '0.75rem' }}>
                {character.charAt(0).toUpperCase()}
              </Avatar>}
              label={character.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
              size="small"
              variant="filled"
              color="secondary"
            />
          ))}
          {story.characters && story.characters.length > 3 && (
            <Chip
              label={`+${story.characters.length - 3} more`}
              size="small"
              variant="outlined"
            />
          )}
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <StoryIcon sx={{ fontSize: 14 }} />
              {story.metadata?.wordCount || 0}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <ScheduleIcon sx={{ fontSize: 14 }} />
              {getReadingTime()}m
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            {formatDate(story.createdAt)}
          </Typography>
        </Box>
      </CardContent>

      <CardActions>
        <Button size="small" startIcon={<ViewIcon />} onClick={(e) => { e.stopPropagation(); onView(story); }}>
          Read
        </Button>
        <Button size="small" startIcon={<EditIcon />} onClick={(e) => { e.stopPropagation(); onEdit(story); }}>
          Edit
        </Button>
        <Button size="small" startIcon={<DownloadIcon />} onClick={(e) => { e.stopPropagation(); onDownload(story); }}>
          Export
        </Button>
      </CardActions>

      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
        onClick={(e) => e.stopPropagation()}
      >
        <MenuItem onClick={() => { onView(story); handleMenuClose(); }}>
          <ViewIcon sx={{ mr: 1 }} />
          View Story
        </MenuItem>
        <MenuItem onClick={() => { onEdit(story); handleMenuClose(); }}>
          <EditIcon sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem onClick={() => { onDownload(story); handleMenuClose(); }}>
          <DownloadIcon sx={{ mr: 1 }} />
          Download
        </MenuItem>
        <MenuItem>
          <ShareIcon sx={{ mr: 1 }} />
          Share
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => { onDelete(story); handleMenuClose(); }} sx={{ color: 'error.main' }}>
          <DeleteIcon sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>
    </Card>
  );
};

const StoryLibrarySkeleton: React.FC<{ viewMode: ViewMode }> = ({ viewMode }) => {
  if (viewMode === 'list') {
    return (
      <Box>
        {Array.from({ length: 5 }).map((_, index) => (
          <Card key={index} sx={{ mb: 1 }}>
            <ListItem sx={{ py: 2 }}>
              <ListItemAvatar>
                <Skeleton variant="circular" width={40} height={40} />
              </ListItemAvatar>
              <ListItemText
                primary={<Skeleton variant="text" width="60%" height={32} />}
                secondary={
                  <Box>
                    <Skeleton variant="text" width="80%" height={20} />
                    <Skeleton variant="text" width="40%" height={16} />
                  </Box>
                }
              />
            </ListItem>
          </Card>
        ))}
      </Box>
    );
  }

  return (
    <Grid container spacing={3}>
      {Array.from({ length: 6 }).map((_, index) => (
        <Grid item xs={12} sm={6} md={4} key={index}>
          <Card>
            <CardContent>
              <Skeleton variant="text" width="80%" height={32} sx={{ mb: 1 }} />
              <Skeleton variant="text" width="100%" height={20} sx={{ mb: 1 }} />
              <Skeleton variant="text" width="60%" height={20} sx={{ mb: 2 }} />
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <Skeleton variant="rectangular" width={60} height={20} />
                <Skeleton variant="rectangular" width={80} height={20} />
              </Box>
              <Skeleton variant="text" width="40%" height={16} />
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default function StoryLibrary() {
  const [stories] = useState<StoryProject[]>(MOCK_STORIES);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('newest');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 9;

  // Filter and sort stories
  const filteredAndSortedStories = useMemo(() => {
    let filtered = stories;

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(story =>
        story.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        story.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        story.characters?.some(char => char.toLowerCase().includes(searchTerm.toLowerCase())) ||
        story.metadata?.tags?.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    // Apply status filter
    if (statusFilter) {
      filtered = filtered.filter(story => story.status === statusFilter);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'newest':
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        case 'oldest':
          return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        case 'title':
          return a.title.localeCompare(b.title);
        case 'wordCount':
          return (b.metadata?.wordCount || 0) - (a.metadata?.wordCount || 0);
        default:
          return 0;
      }
    });

    return filtered;
  }, [stories, searchTerm, statusFilter, sortBy]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedStories.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedStories = filteredAndSortedStories.slice(startIndex, startIndex + itemsPerPage);

  const handleView = (story: StoryProject) => {
    console.log('View story:', story.title);
    // TODO: Navigate to story details or open in modal
  };

  const handleEdit = (story: StoryProject) => {
    console.log('Edit story:', story.title);
    // TODO: Navigate to story editor
  };

  const handleDelete = (story: StoryProject) => {
    console.log('Delete story:', story.title);
    // TODO: Show confirmation dialog and delete story
  };

  const handleDownload = (story: StoryProject) => {
    const blob = new Blob([story.storyContent || ''], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${story.title.replace(/[^a-z0-9]/gi, '_')}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const isLoading = false; // Set to true when loading from API

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" sx={{ mb: 1, fontWeight: 700 }}>
          Story Library
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
          Browse and manage your generated stories
        </Typography>

        {/* Filters and Controls */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search stories, characters, or tags..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon color="action" />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>

            <Grid item xs={12} sm={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>Status</InputLabel>
                <Select
                  value={statusFilter}
                  label="Status"
                  onChange={(e) => setStatusFilter(e.target.value)}
                  startAdornment={<FilterIcon sx={{ mr: 1, color: 'action.active' }} />}
                >
                  <MenuItem value="">All Status</MenuItem>
                  <MenuItem value="completed">Completed</MenuItem>
                  <MenuItem value="draft">Draft</MenuItem>
                  <MenuItem value="generating">Generating</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>Sort by</InputLabel>
                <Select
                  value={sortBy}
                  label="Sort by"
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  startAdornment={<SortIcon sx={{ mr: 1, color: 'action.active' }} />}
                >
                  <MenuItem value="newest">Newest First</MenuItem>
                  <MenuItem value="oldest">Oldest First</MenuItem>
                  <MenuItem value="title">Title A-Z</MenuItem>
                  <MenuItem value="wordCount">Word Count</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={2}>
              <ToggleButtonGroup
                value={viewMode}
                exclusive
                onChange={(_, newViewMode) => newViewMode && setViewMode(newViewMode)}
                size="small"
                fullWidth
              >
                <ToggleButton value="grid" aria-label="grid view">
                  <GridViewIcon />
                </ToggleButton>
                <ToggleButton value="list" aria-label="list view">
                  <ListViewIcon />
                </ToggleButton>
              </ToggleButtonGroup>
            </Grid>

            <Grid item xs={12} md={2}>
              <Typography variant="body2" color="text.secondary" align="right">
                {filteredAndSortedStories.length} stories found
              </Typography>
            </Grid>
          </Grid>
        </Paper>
      </Box>

      {/* Stories Display */}
      {isLoading ? (
        <StoryLibrarySkeleton viewMode={viewMode} />
      ) : paginatedStories.length > 0 ? (
        <>
          {viewMode === 'grid' ? (
            <Grid container spacing={3}>
              {paginatedStories.map((story) => (
                <Grid item xs={12} sm={6} md={4} key={story.id}>
                  <StoryCard
                    story={story}
                    viewMode={viewMode}
                    onView={handleView}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onDownload={handleDownload}
                  />
                </Grid>
              ))}
            </Grid>
          ) : (
            <Box>
              {paginatedStories.map((story) => (
                <StoryCard
                  key={story.id}
                  story={story}
                  viewMode={viewMode}
                  onView={handleView}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onDownload={handleDownload}
                />
              ))}
            </Box>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <Pagination
                count={totalPages}
                page={currentPage}
                onChange={(_, page) => setCurrentPage(page)}
                color="primary"
                size="large"
              />
            </Box>
          )}
        </>
      ) : (
        <Paper sx={{ p: 6, textAlign: 'center' }}>
          <StoryIcon sx={{ fontSize: 72, color: 'text.secondary', mb: 3 }} />
          <Typography variant="h4" color="text.secondary" sx={{ mb: 2, fontWeight: 600 }}>
            {searchTerm || statusFilter ? 'No stories found' : 'No stories yet'}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: 500, mx: 'auto' }}>
            {searchTerm || statusFilter
              ? 'Try adjusting your search terms or filters to find what you\'re looking for.'
              : 'Start creating stories in the Workshop to build your library of AI-generated narratives.'}
          </Typography>
          <Button
            variant="contained"
            size="large"
            startIcon={<StoryIcon />}
            onClick={() => console.log('Navigate to workshop')}
            sx={{ fontWeight: 600 }}
          >
            Create Your First Story
          </Button>
        </Paper>
      )}
    </Box>
  );
}
