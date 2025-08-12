import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Avatar,
  LinearProgress,
  IconButton,
  Tooltip,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Person as PersonIcon,
  AutoStories as StoryIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon,
  Storage as StorageIcon,
  Analytics as AnalyticsIcon,
  TrendingUp as TrendingUpIcon,
  AccessTime as TimeIcon,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import api from '../services/api';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  // Fetch dashboard data
  const { data: characters, isLoading: charactersLoading } = useQuery(
    'characters',
    api.getCharacters
  );

  const { data: campaigns, isLoading: campaignsLoading } = useQuery(
    'campaigns',
    api.getCampaigns
  );

  const { data: systemStatus, isLoading: statusLoading } = useQuery(
    'system-status',
    api.getHealth,
    {
      refetchInterval: 10000, // Refresh every 10 seconds
    }
  );

  // Mock data for recent activities and statistics
  const recentProjects = [
    {
      id: '1',
      title: 'The Last Stand of Cadia',
      status: 'completed',
      characters: ['krieg', 'ork'],
      createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
      wordCount: 1250,
    },
    {
      id: '2',
      title: 'Shadows in the Underhive',
      status: 'draft',
      characters: ['isabella_varr'],
      createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
      wordCount: 850,
    },
    {
      id: '3',
      title: 'Brothers in Arms',
      status: 'generating',
      characters: ['krieg', 'test'],
      createdAt: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
      wordCount: 0,
    },
  ];

  const systemMetrics = {
    totalCharacters: characters?.length || 0,
    totalCampaigns: campaigns?.length || 0,
    totalStories: 12,
    avgGenerationTime: 2.3,
    cacheHitRate: 89,
    systemUptime: 95.8,
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'generating':
        return 'info';
      case 'draft':
        return 'warning';
      default:
        return 'default';
    }
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffHours > 0) {
      return `${diffHours}h ago`;
    } else if (diffMinutes > 0) {
      return `${diffMinutes}m ago`;
    } else {
      return 'Just now';
    }
  };

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Welcome Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" sx={{ mb: 1, fontWeight: 700 }}>
          Welcome to Novel Engine
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
          Create compelling stories through AI-powered multi-agent interactions
        </Typography>

        {/* Quick Actions */}
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            size="large"
            startIcon={<AddIcon />}
            onClick={() => navigate('/characters')}
            sx={{ fontWeight: 600 }}
          >
            Create Character
          </Button>
          <Button
            variant="outlined"
            size="large"
            startIcon={<PlayIcon />}
            onClick={() => navigate('/workshop')}
            sx={{ fontWeight: 600 }}
          >
            Start Story
          </Button>
          <Button
            variant="text"
            size="large"
            startIcon={<StoryIcon />}
            onClick={() => navigate('/library')}
            sx={{ fontWeight: 600 }}
          >
            Browse Library
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* System Overview Cards */}
        <Grid item xs={12} md={8}>
          <Grid container spacing={2}>
            {/* Characters Card */}
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center', pb: 1 }}>
                  <Avatar sx={{ bgcolor: 'primary.main', mx: 'auto', mb: 1 }}>
                    <PersonIcon />
                  </Avatar>
                  <Typography variant="h4" component="div" sx={{ fontWeight: 700 }}>
                    {charactersLoading ? '...' : systemMetrics.totalCharacters}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Characters
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* Stories Card */}
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center', pb: 1 }}>
                  <Avatar sx={{ bgcolor: 'secondary.main', mx: 'auto', mb: 1 }}>
                    <StoryIcon />
                  </Avatar>
                  <Typography variant="h4" component="div" sx={{ fontWeight: 700 }}>
                    {systemMetrics.totalStories}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Stories
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* Performance Card */}
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center', pb: 1 }}>
                  <Avatar sx={{ bgcolor: 'info.main', mx: 'auto', mb: 1 }}>
                    <SpeedIcon />
                  </Avatar>
                  <Typography variant="h4" component="div" sx={{ fontWeight: 700 }}>
                    {systemMetrics.avgGenerationTime}s
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Avg Time
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* Cache Hit Rate Card */}
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center', pb: 1 }}>
                  <Avatar sx={{ bgcolor: 'success.main', mx: 'auto', mb: 1 }}>
                    <MemoryIcon />
                  </Avatar>
                  <Typography variant="h4" component="div" sx={{ fontWeight: 700 }}>
                    {systemMetrics.cacheHitRate}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Cache Hit
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* System Performance */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <AnalyticsIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
                  System Performance
                </Typography>
              </Box>
              
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">System Uptime</Typography>
                      <Typography variant="body2" color="success.main" sx={{ fontWeight: 600 }}>
                        {systemMetrics.systemUptime}%
                      </Typography>
                    </Box>
                    <LinearProgress 
                      variant="determinate" 
                      value={systemMetrics.systemUptime} 
                      color="success"
                      sx={{ borderRadius: 1, height: 6 }}
                    />
                  </Box>
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">Cache Efficiency</Typography>
                      <Typography variant="body2" color="info.main" sx={{ fontWeight: 600 }}>
                        {systemMetrics.cacheHitRate}%
                      </Typography>
                    </Box>
                    <LinearProgress 
                      variant="determinate" 
                      value={systemMetrics.cacheHitRate} 
                      color="info"
                      sx={{ borderRadius: 1, height: 6 }}
                    />
                  </Box>
                </Grid>
              </Grid>

              {/* API Status */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2 }}>
                <Chip
                  label={statusLoading ? 'Checking...' : `API: ${systemStatus?.api || 'Unknown'}`}
                  color={statusLoading ? 'default' : (systemStatus?.api === 'running' ? 'success' : 'error')}
                  size="small"
                />
                <Chip
                  label={`Config: ${systemStatus?.config || 'Unknown'}`}
                  color={systemStatus?.config === 'loaded' ? 'success' : 'warning'}
                  size="small"
                />
                <Chip
                  label={`Version: ${systemStatus?.version || '1.0.0'}`}
                  variant="outlined"
                  size="small"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Projects */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: 'fit-content' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
                  Recent Projects
                </Typography>
                <Tooltip title="View All">
                  <IconButton size="small" onClick={() => navigate('/library')}>
                    <TrendingUpIcon />
                  </IconButton>
                </Tooltip>
              </Box>

              <List sx={{ p: 0 }}>
                {recentProjects.map((project, index) => (
                  <React.Fragment key={project.id}>
                    <ListItem sx={{ px: 0 }}>
                      <ListItemAvatar>
                        <Avatar sx={{ bgcolor: 'primary.main' }}>
                          <StoryIcon />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                              {project.title}
                            </Typography>
                            <Chip
                              label={project.status}
                              size="small"
                              color={getStatusColor(project.status)}
                              variant="outlined"
                            />
                          </Box>
                        }
                        secondary={
                          <Box sx={{ mt: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">
                              {project.characters.join(', ')} • {project.wordCount} words
                            </Typography>
                            <br />
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                              <TimeIcon sx={{ fontSize: 12 }} />
                              <Typography variant="caption" color="text.secondary">
                                {formatTimeAgo(project.createdAt)}
                              </Typography>
                            </Box>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < recentProjects.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>

              <Box sx={{ mt: 2 }}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => navigate('/workshop')}
                >
                  Create New Project
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Character Highlights */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
                  Your Characters
                </Typography>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => navigate('/characters')}
                >
                  Add Character
                </Button>
              </Box>

              {charactersLoading ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography color="text.secondary">Loading characters...</Typography>
                </Box>
              ) : characters && characters.length > 0 ? (
                <Grid container spacing={2}>
                  {characters.slice(0, 6).map((characterName) => (
                    <Grid item xs={6} sm={4} md={2} key={characterName}>
                      <Card variant="outlined" sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}>
                        <CardContent sx={{ textAlign: 'center', p: 2 }}>
                          <Avatar sx={{ mx: 'auto', mb: 1, bgcolor: 'secondary.main' }}>
                            {characterName.charAt(0).toUpperCase()}
                          </Avatar>
                          <Typography variant="subtitle2" noWrap>
                            {characterName}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Character
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              ) : (
                <Paper sx={{ p: 4, textAlign: 'center', bgcolor: 'action.hover' }}>
                  <PersonIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                    No Characters Yet
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Create your first character to start building stories
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => navigate('/characters')}
                  >
                    Create Character
                  </Button>
                </Paper>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;