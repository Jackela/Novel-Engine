# Frontend Integration Guide

**Version**: 1.0.0  
**Target Audience**: Frontend Developers  
**Integration Scope**: React/TypeScript → Novel Engine API  
**Date**: 2025-08-12

## 🎯 Overview

This guide provides complete integration patterns for connecting the React/TypeScript frontend with the Novel Engine API. All examples are production-ready and follow modern React patterns.

## 📡 API Client Setup

### Core Configuration
```typescript
// src/services/api.ts
import axios, { AxiosInstance } from 'axios';

class NovelEngineAPI {
  private client: AxiosInstance;

  constructor(baseURL: string = process.env.REACT_APP_API_URL || 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        console.log(`🌐 API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => Promise.reject(this.handleError(error))
    );
  }

  private handleError(error: any): Error {
    if (error.response) {
      const message = error.response.data?.detail || 'Server error';
      return new Error(`API Error (${error.response.status}): ${message}`);
    } else if (error.request) {
      return new Error('Network error: Unable to connect to server');
    }
    return new Error(`Request error: ${error.message}`);
  }
}
```

### Environment Configuration
```bash
# .env.development
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_ENABLE_LOGGING=true

# .env.production
REACT_APP_API_URL=https://api.novelengine.app
REACT_APP_WS_URL=wss://api.novelengine.app/ws
REACT_APP_ENABLE_LOGGING=false
```

## 🔄 React Query Integration

### Query Client Setup
```typescript
// src/App.tsx
import { QueryClient, QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    },
    mutations: {
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <YourAppComponents />
      {process.env.NODE_ENV === 'development' && <ReactQueryDevtools />}
    </QueryClientProvider>
  );
}
```

### Custom Hooks for API Integration

#### System Health Hook
```typescript
// src/hooks/useSystemHealth.ts
import { useQuery } from 'react-query';
import api from '../services/api';

export function useSystemHealth() {
  return useQuery(
    'system-health',
    api.getHealth,
    {
      refetchInterval: 30000, // Check every 30 seconds
      retry: false,
      onError: (error) => {
        console.warn('System health check failed:', error);
      },
    }
  );
}

// Usage in component
function Navbar() {
  const { data: health, isLoading, isError } = useSystemHealth();
  
  const getHealthColor = () => {
    if (isLoading) return 'default';
    if (isError || !health) return 'error';
    return health.api === 'healthy' ? 'success' : 'warning';
  };

  return (
    <Chip 
      label={isLoading ? 'Checking...' : health?.api || 'Offline'}
      color={getHealthColor()}
    />
  );
}
```

#### Character Management Hooks
```typescript
// src/hooks/useCharacters.ts
import { useQuery, useMutation, useQueryClient } from 'react-query';
import api from '../services/api';
import { CharacterFormData } from '../types';

export function useCharacters() {
  return useQuery('characters', api.getCharacters, {
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useCharacterDetails(name: string | null) {
  return useQuery(
    ['character-details', name],
    () => name ? api.getCharacterDetails(name) : null,
    {
      enabled: !!name,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
}

export function useCreateCharacter() {
  const queryClient = useQueryClient();

  return useMutation(
    ({ data, files }: { data: CharacterFormData; files?: File[] }) => 
      api.createCharacter(data, files),
    {
      onSuccess: () => {
        // Invalidate and refetch character list
        queryClient.invalidateQueries('characters');
      },
      onError: (error) => {
        console.error('Character creation failed:', error);
      },
    }
  );
}

// Usage in component
function CharacterStudio() {
  const { data: characters, isLoading, refetch } = useCharacters();
  const createCharacterMutation = useCreateCharacter();

  const handleCreateCharacter = async (formData: CharacterFormData) => {
    try {
      await createCharacterMutation.mutateAsync({ data: formData });
      // Character list will be automatically refreshed
      toast.success('Character created successfully!');
    } catch (error) {
      toast.error('Failed to create character');
    }
  };

  return (
    <div>
      {isLoading ? (
        <LoadingSkeleton />
      ) : (
        <CharacterGrid characters={characters} />
      )}
      <CreateCharacterDialog onSubmit={handleCreateCharacter} />
    </div>
  );
}
```

#### Story Generation Hook
```typescript
// src/hooks/useStoryGeneration.ts
import { useMutation } from 'react-query';
import api from '../services/api';
import { StoryFormData } from '../types';

export function useStoryGeneration() {
  return useMutation(
    (storyData: StoryFormData) => api.runSimulation(storyData),
    {
      onMutate: () => {
        // Show loading state immediately
        console.log('Story generation started...');
      },
      onSuccess: (data) => {
        console.log('Story generated successfully:', data);
      },
      onError: (error) => {
        console.error('Story generation failed:', error);
      },
    }
  );
}

// Usage with loading states
function StoryWorkshop() {
  const generateStory = useStoryGeneration();

  const handleGenerateStory = async (formData: StoryFormData) => {
    try {
      const result = await generateStory.mutateAsync(formData);
      setGeneratedStory(result.data);
    } catch (error) {
      toast.error('Story generation failed');
    }
  };

  return (
    <div>
      <StoryForm onSubmit={handleGenerateStory} />
      {generateStory.isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <CircularProgress size={20} />
          <Typography>Generating story... (~45 seconds)</Typography>
        </Box>
      )}
      {generateStory.data && (
        <StoryDisplay story={generateStory.data} />
      )}
    </div>
  );
}
```

## 🎨 Component Integration Patterns

### Error Boundary Implementation
```typescript
// src/components/ErrorBoundary.tsx
import React, { Component, ReactNode } from 'react';
import { Alert, Button, Box, Typography } from '@mui/material';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <Box sx={{ p: 3 }}>
          <Alert severity="error" sx={{ mb: 2 }}>
            <Typography variant="h6">Something went wrong</Typography>
            <Typography variant="body2">
              {this.state.error?.message || 'An unexpected error occurred'}
            </Typography>
          </Alert>
          <Button 
            variant="outlined" 
            onClick={() => this.setState({ hasError: false, error: undefined })}
          >
            Try Again
          </Button>
        </Box>
      );
    }

    return this.props.children;
  }
}
```

### Loading States with Skeletons
```typescript
// src/components/LoadingStates.tsx
import React from 'react';
import { Skeleton, Card, CardContent, Grid, Box } from '@mui/material';

export function CharacterCardSkeleton() {
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <Skeleton variant="circular" width={80} height={80} sx={{ mb: 2 }} />
          <Skeleton variant="text" width="60%" height={32} sx={{ mb: 1 }} />
          <Skeleton variant="text" width="40%" height={24} sx={{ mb: 2 }} />
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <Skeleton variant="rectangular" width={60} height={24} />
            <Skeleton variant="rectangular" width={60} height={24} />
            <Skeleton variant="rectangular" width={60} height={24} />
          </Box>
          <Skeleton variant="rectangular" width="100%" height={36} />
        </Box>
      </CardContent>
    </Card>
  );
}

export function CharacterGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <Grid container spacing={3}>
      {Array.from({ length: count }).map((_, index) => (
        <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
          <CharacterCardSkeleton />
        </Grid>
      ))}
    </Grid>
  );
}
```

### Form Integration with Validation
```typescript
// src/components/CharacterCreationDialog.tsx
import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { useCreateCharacter } from '../hooks/useCharacters';
import { CharacterFormData } from '../types';

interface Props {
  open: boolean;
  onClose: () => void;
  onCharacterCreated: () => void;
}

export default function CharacterCreationDialog({ open, onClose, onCharacterCreated }: Props) {
  const [formData, setFormData] = useState<CharacterFormData>({
    name: '',
    description: '',
    faction: '',
    role: '',
    stats: {
      strength: 5,
      dexterity: 5,
      intelligence: 5,
      willpower: 5,
      perception: 5,
      charisma: 5,
    },
    equipment: [],
    relationships: [],
  });

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const createCharacter = useCreateCharacter();

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.name.trim()) {
      errors.name = 'Character name is required';
    } else if (formData.name.length < 3) {
      errors.name = 'Name must be at least 3 characters';
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.name)) {
      errors.name = 'Name can only contain letters, numbers, and underscores';
    }

    if (!formData.description.trim()) {
      errors.description = 'Description is required';
    } else if (formData.description.length < 10) {
      errors.description = 'Description must be at least 10 characters';
    }

    // Validate stats range
    Object.entries(formData.stats).forEach(([stat, value]) => {
      if (value < 1 || value > 10) {
        errors[stat] = `${stat} must be between 1 and 10`;
      }
    });

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      await createCharacter.mutateAsync({ data: formData });
      onCharacterCreated();
      onClose();
      setFormData({
        name: '',
        description: '',
        faction: '',
        role: '',
        stats: { strength: 5, dexterity: 5, intelligence: 5, willpower: 5, perception: 5, charisma: 5 },
        equipment: [],
        relationships: [],
      });
    } catch (error) {
      // Error handling is done in the mutation
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>Create New Character</DialogTitle>
        <DialogContent>
          {createCharacter.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {createCharacter.error?.message || 'Failed to create character'}
            </Alert>
          )}

          <TextField
            autoFocus
            margin="dense"
            name="name"
            label="Character Name"
            type="text"
            fullWidth
            variant="outlined"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            error={!!validationErrors.name}
            helperText={validationErrors.name || 'Use letters, numbers, and underscores only'}
            sx={{ mb: 2 }}
          />

          <TextField
            margin="dense"
            name="description"
            label="Character Description"
            multiline
            rows={4}
            fullWidth
            variant="outlined"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            error={!!validationErrors.description}
            helperText={validationErrors.description || 'Describe your character\'s background and personality'}
            sx={{ mb: 2 }}
          />

          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Faction</InputLabel>
              <Select
                value={formData.faction}
                label="Faction"
                onChange={(e) => setFormData({ ...formData, faction: e.target.value })}
              >
                <MenuItem value="Imperial">Imperial</MenuItem>
                <MenuItem value="Chaos">Chaos</MenuItem>
                <MenuItem value="Ork">Ork</MenuItem>
                <MenuItem value="Death Korps of Krieg">Death Korps of Krieg</MenuItem>
                <MenuItem value="Other">Other</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Role"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              placeholder="e.g., Guardsman, Warboss"
            />
          </Box>

          {/* Character Stats */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Character Stats (1-10)</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2 }}>
              {Object.entries(formData.stats).map(([stat, value]) => (
                <TextField
                  key={stat}
                  label={stat.charAt(0).toUpperCase() + stat.slice(1)}
                  type="number"
                  inputProps={{ min: 1, max: 10 }}
                  value={value}
                  onChange={(e) => setFormData({
                    ...formData,
                    stats: { ...formData.stats, [stat]: parseInt(e.target.value) || 1 }
                  })}
                  error={!!validationErrors[stat]}
                  helperText={validationErrors[stat]}
                />
              ))}
            </Box>
          </Box>
        </DialogContent>

        <DialogActions>
          <Button onClick={onClose} disabled={createCharacter.isLoading}>
            Cancel
          </Button>
          <Button 
            type="submit" 
            variant="contained" 
            disabled={createCharacter.isLoading}
          >
            {createCharacter.isLoading ? 'Creating...' : 'Create Character'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
```

## 🔄 Real-time Updates

### Polling Strategy
```typescript
// src/hooks/usePolling.ts
import { useQuery } from 'react-query';
import { useEffect, useRef } from 'react';

export function useSystemStatusWithPolling() {
  const intervalRef = useRef<number>();

  const query = useQuery(
    'system-status-polling',
    api.getSystemStatus,
    {
      refetchInterval: 10000, // Poll every 10 seconds
      refetchIntervalInBackground: false,
      onError: () => {
        // Exponential backoff on errors
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          setTimeout(() => {
            query.refetch();
          }, Math.min(30000, query.failureCount * 5000));
        }
      },
    }
  );

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return query;
}
```

### WebSocket Integration (Planned)
```typescript
// src/hooks/useWebSocket.ts (Future implementation)
import { useEffect, useRef, useState } from 'react';

interface WebSocketHook {
  isConnected: boolean;
  sendMessage: (message: any) => void;
  lastMessage: any;
}

export function useWebSocket(url: string): WebSocketHook {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setLastMessage(message);
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    };

    return () => {
      ws.current?.close();
    };
  }, [url]);

  const sendMessage = (message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  };

  return { isConnected, sendMessage, lastMessage };
}
```

## 🎨 UI Patterns

### Toast Notifications
```typescript
// src/contexts/NotificationContext.tsx
import React, { createContext, useContext, useState } from 'react';
import { Snackbar, Alert } from '@mui/material';

interface Notification {
  id: string;
  message: string;
  severity: 'success' | 'error' | 'warning' | 'info';
}

interface NotificationContextType {
  showNotification: (message: string, severity?: Notification['severity']) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notification, setNotification] = useState<Notification | null>(null);

  const showNotification = (message: string, severity: Notification['severity'] = 'info') => {
    setNotification({
      id: Date.now().toString(),
      message,
      severity,
    });
  };

  const handleClose = () => {
    setNotification(null);
  };

  return (
    <NotificationContext.Provider value={{ showNotification }}>
      {children}
      <Snackbar
        open={!!notification}
        autoHideDuration={6000}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        {notification && (
          <Alert onClose={handleClose} severity={notification.severity}>
            {notification.message}
          </Alert>
        )}
      </Snackbar>
    </NotificationContext.Provider>
  );
}

export function useNotification() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
}
```

### Responsive Design Patterns
```typescript
// src/hooks/useResponsive.ts
import { useTheme, useMediaQuery } from '@mui/material';

export function useResponsive() {
  const theme = useTheme();
  
  return {
    isMobile: useMediaQuery(theme.breakpoints.down('sm')),
    isTablet: useMediaQuery(theme.breakpoints.between('sm', 'md')),
    isDesktop: useMediaQuery(theme.breakpoints.up('md')),
    isLarge: useMediaQuery(theme.breakpoints.up('lg')),
  };
}

// Usage in components
function CharacterGrid() {
  const { isMobile, isTablet } = useResponsive();
  
  const getGridColumns = () => {
    if (isMobile) return 1;
    if (isTablet) return 2;
    return 4;
  };

  return (
    <Grid container spacing={3}>
      {characters.map((character) => (
        <Grid item xs={12} sm={6} md={4} lg={3} key={character.id}>
          <CharacterCard character={character} compact={isMobile} />
        </Grid>
      ))}
    </Grid>
  );
}
```

## 🚀 Performance Optimization

### Component Optimization
```typescript
// src/components/optimized/VirtualizedList.tsx
import React from 'react';
import { FixedSizeList as List } from 'react-window';
import { Box } from '@mui/material';

interface VirtualizedListProps {
  items: any[];
  height: number;
  itemHeight: number;
  renderItem: (props: { index: number; style: any }) => React.ReactNode;
}

export function VirtualizedList({ items, height, itemHeight, renderItem }: VirtualizedListProps) {
  return (
    <Box sx={{ height, width: '100%' }}>
      <List
        height={height}
        itemCount={items.length}
        itemSize={itemHeight}
        itemData={items}
      >
        {renderItem}
      </List>
    </Box>
  );
}

// Usage for large character lists
function CharacterLibrary() {
  const { data: characters = [] } = useCharacters();

  const renderCharacterItem = ({ index, style }: { index: number; style: any }) => (
    <div style={style}>
      <CharacterListItem character={characters[index]} />
    </div>
  );

  if (characters.length > 50) {
    return (
      <VirtualizedList
        items={characters}
        height={600}
        itemHeight={80}
        renderItem={renderCharacterItem}
      />
    );
  }

  return <RegularCharacterGrid characters={characters} />;
}
```

### Memoization Patterns
```typescript
// src/components/optimized/MemoizedComponents.tsx
import React, { memo, useMemo } from 'react';

// Memoize expensive character card renders
export const CharacterCard = memo(({ character, onView, onEdit, onDelete }: CharacterCardProps) => {
  const factionColor = useMemo(() => getFactionColor(character.faction), [character.faction]);
  const displayStats = useMemo(() => formatCharacterStats(character.stats), [character.stats]);

  return (
    <Card sx={{ bgcolor: factionColor }}>
      {/* Card content */}
    </Card>
  );
});

// Memoize complex calculations
export function useCharacterMetrics(characters: Character[]) {
  return useMemo(() => {
    const factionCounts = characters.reduce((acc, char) => {
      acc[char.faction] = (acc[char.faction] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const averageStats = characters.reduce((acc, char) => {
      Object.entries(char.stats).forEach(([stat, value]) => {
        acc[stat] = (acc[stat] || 0) + value;
      });
      return acc;
    }, {} as Record<string, number>);

    Object.keys(averageStats).forEach(stat => {
      averageStats[stat] = Math.round(averageStats[stat] / characters.length);
    });

    return { factionCounts, averageStats };
  }, [characters]);
}
```

## 🧪 Testing Integration

### Component Testing
```typescript
// src/components/__tests__/CharacterCard.test.tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CharacterCard from '../CharacterCard';

const createTestWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const theme = createTheme();

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
};

describe('CharacterCard', () => {
  const mockCharacter = {
    id: 'test',
    name: 'Test Character',
    faction: 'Imperial',
    role: 'Guardsman',
    stats: { strength: 7, intelligence: 6, charisma: 5 },
  };

  it('renders character information correctly', () => {
    render(
      <CharacterCard
        characterName="test"
        onView={jest.fn()}
        onEdit={jest.fn()}
        onDelete={jest.fn()}
      />,
      { wrapper: createTestWrapper() }
    );

    expect(screen.getByText('Test Character')).toBeInTheDocument();
    expect(screen.getByText('Imperial')).toBeInTheDocument();
    expect(screen.getByText('STR 7')).toBeInTheDocument();
  });

  it('calls onView when view button is clicked', () => {
    const mockOnView = jest.fn();
    
    render(
      <CharacterCard
        characterName="test"
        onView={mockOnView}
        onEdit={jest.fn()}
        onDelete={jest.fn()}
      />,
      { wrapper: createTestWrapper() }
    );

    fireEvent.click(screen.getByText('View'));
    expect(mockOnView).toHaveBeenCalledTimes(1);
  });
});
```

### API Integration Testing
```typescript
// src/services/__tests__/api.test.ts
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import api from '../api';

const server = setupServer(
  rest.get('http://localhost:8000/health', (req, res, ctx) => {
    return res(ctx.json({ api: 'healthy', version: '1.0.0' }));
  }),

  rest.get('http://localhost:8000/characters', (req, res, ctx) => {
    return res(ctx.json({ characters: ['test_character'] }));
  }),

  rest.post('http://localhost:8000/characters', (req, res, ctx) => {
    return res(ctx.json({ name: 'new_character', success: true }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('NovelEngineAPI', () => {
  it('fetches system health', async () => {
    const health = await api.getHealth();
    expect(health.api).toBe('healthy');
    expect(health.version).toBe('1.0.0');
  });

  it('fetches character list', async () => {
    const characters = await api.getCharacters();
    expect(characters).toEqual(['test_character']);
  });

  it('creates a new character', async () => {
    const formData = {
      name: 'new_character',
      description: 'Test character description',
      faction: 'Imperial',
      role: 'Guardsman',
      stats: { strength: 5, dexterity: 5, intelligence: 5, willpower: 5, perception: 5, charisma: 5 },
      equipment: [],
      relationships: [],
    };

    const result = await api.createCharacter(formData);
    expect(result.success).toBe(true);
    expect(result.data.name).toBe('new_character');
  });
});
```

---

This integration guide provides production-ready patterns for connecting the React frontend with the Novel Engine API. All examples follow modern React best practices and include proper error handling, loading states, and performance optimizations.

**Next Steps**: 
1. Implement remaining component dialogs (CharacterCreationDialog, CharacterDetailsDialog)
2. Add StoryWorkshop, StoryLibrary, and SystemMonitor components
3. Set up comprehensive testing suite
4. Configure production deployment pipeline
