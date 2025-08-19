# Character Selection Component - UI Design Specification

## 1. Component Overview

The Character Selection Component is a React-based UI component that serves as the primary interface for users to select characters for Warhammer 40k multi-agent simulations. This component acts as the gateway between the user and the simulation execution pipeline, allowing users to choose which characters will participate in epic narrative scenarios.

### Purpose
- Enable users to select 2-6 characters from the available character roster
- Provide visual feedback for character selection state
- Validate selection constraints before allowing simulation execution
- Integrate seamlessly with the existing FastAPI backend and simulation workflow

### Role in Simulation Workflow
1. **Entry Point**: First interactive step in the simulation pipeline
2. **Character Validation**: Ensures selected characters exist and are properly loaded
3. **Constraint Enforcement**: Validates minimum/maximum character requirements
4. **Data Preparation**: Formats selected character data for simulation execution
5. **User Experience**: Provides intuitive character browsing and selection interface

### Context within Novel Engine Application
The component integrates with the existing React frontend (built with React 19 + Vite) and communicates with the FastAPI backend through RESTful API endpoints. It serves as a bridge between the user interface and the character management system, leveraging the CharacterFactory and existing character data structure.

## 2. State Management

The component requires the following React state variables to manage character selection functionality:

### Core State Variables

```javascript
// Array of character objects fetched from the API
const [charactersList, setCharactersList] = useState([]);
// Structure: [{ name: string, details?: object }, ...]

// Array of selected character names
const [selectedCharacters, setSelectedCharacters] = useState([]);
// Structure: ['krieg', 'ork', ...]

// Boolean flag for API loading states
const [isLoading, setIsLoading] = useState(true);

// Error handling for API failures and validation
const [error, setError] = useState(null);
// Structure: string | { message: string, type: 'api' | 'validation' }

// Character details cache for performance optimization
const [characterDetails, setCharacterDetails] = useState({});
// Structure: { 'krieg': { narrative_context: string, structured_data: object }, ... }

// Loading state for individual character detail fetches
const [detailsLoading, setDetailsLoading] = useState({});
// Structure: { 'krieg': true, 'ork': false, ... }

// Validation state for selection constraints
const [validationError, setValidationError] = useState(null);
// Structure: string | null

// UI state for user interactions
const [showConfirmDialog, setShowConfirmDialog] = useState(false);
```

### State Management Patterns
- Use `useState` hooks for component-level state management
- Implement proper state cleanup on component unmount
- Consider `useCallback` for memoized event handlers
- Use `useMemo` for computed values (e.g., selection validation)

## 3. API Interaction

### Primary API Endpoint
The component must integrate with the existing FastAPI backend endpoints:

#### GET /characters
**Purpose**: Fetch list of available characters on component mount

**Expected Response Format**:
```json
{
  "characters": ["krieg", "ork", "test"]
}
```

**Error Handling**:
- 404: Characters directory not found
- 500: Internal server error
- Network errors: Connection timeout, server unavailable

#### GET /characters/{character_name} (Optional Enhancement)
**Purpose**: Fetch detailed character information for preview functionality

**Expected Response Format**:
```json
{
  "character_name": "krieg",
  "narrative_context": "Trooper 86 of the Death Korps of Krieg...",
  "structured_data": {
    "name": "Trooper 86",
    "factions": ["Astra Militarum", "Death Korps of Krieg"],
    "personality_traits": ["Fatalistic", "Grim", "Loyal to the Emperor"]
  },
  "file_count": {
    "md": 1,
    "yaml": 1
  }
}
```

### API Integration Implementation

```javascript
// Base API configuration
const API_BASE_URL = 'http://localhost:8000';
const API_TIMEOUT = 5000;

// API call with error handling
useEffect(() => {
  const fetchCharacters = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await axios.get(`${API_BASE_URL}/characters`, {
        timeout: API_TIMEOUT
      });
      
      setCharactersList(response.data.characters);
      setIsLoading(false);
    } catch (err) {
      console.error('Error fetching characters:', err);
      
      if (err.code === 'ECONNABORTED') {
        setError('Request timeout - Server may be slow to respond');
      } else if (err.response?.status === 404) {
        setError('No characters found - Please ensure character data is available');
      } else if (err.response?.status >= 500) {
        setError('Server error - Please try again later');
      } else {
        setError('Cannot connect to server - Please ensure the backend is running');
      }
      
      setIsLoading(false);
    }
  };

  fetchCharacters();
}, []);
```

### Loading State Management
- Display loading spinner during initial character fetch
- Show individual loading indicators for character detail requests
- Implement retry mechanism for failed API calls
- Provide graceful degradation when API is unavailable

### Error Recovery
- Retry button for network failures
- Fallback UI when characters cannot be loaded
- User-friendly error messages for different failure scenarios
- Automatic retry with exponential backoff for transient errors

## 4. User Interactions

### Character Card Click Behavior
**Primary Interaction**: Toggle selection state when character card is clicked

```javascript
const handleCharacterClick = useCallback((characterName) => {
  setSelectedCharacters(prev => {
    if (prev.includes(characterName)) {
      // Deselect character
      return prev.filter(name => name !== characterName);
    } else {
      // Select character (with maximum validation)
      if (prev.length >= 6) {
        setValidationError('Maximum 6 characters allowed');
        return prev;
      }
      return [...prev, characterName];
    }
  });
  
  // Clear validation error when user makes valid selection
  if (validationError) {
    setValidationError(null);
  }
}, [validationError]);
```

### Selection Validation Logic

#### Minimum Requirements
- **Constraint**: At least 2 characters must be selected
- **Validation**: Real-time validation as user selects/deselects
- **Error Message**: "Please select at least 2 characters to start simulation"
- **UI Behavior**: Confirm button remains disabled until requirement met

#### Maximum Requirements
- **Constraint**: No more than 6 characters can be selected
- **Validation**: Prevent selection beyond limit
- **Error Message**: "Maximum 6 characters allowed for simulation"
- **UI Behavior**: Additional selections blocked, visual feedback provided

#### Validation Implementation
```javascript
const selectionValidation = useMemo(() => {
  const count = selectedCharacters.length;
  
  if (count < 2) {
    return {
      isValid: false,
      message: 'Please select at least 2 characters to start simulation',
      type: 'minimum'
    };
  }
  
  if (count > 6) {
    return {
      isValid: false,
      message: 'Maximum 6 characters allowed for simulation',
      type: 'maximum'
    };
  }
  
  return {
    isValid: true,
    message: null,
    type: null
  };
}, [selectedCharacters]);
```

### Visual Feedback States

#### Character Card States
1. **Unselected**: Default appearance with subtle hover effects
2. **Selected**: Highlighted border, background color change, checkmark icon
3. **Hover**: Subtle scale/shadow animation for interactive feedback
4. **Disabled**: Dimmed appearance when maximum selection reached

#### Selection Counter
- Display current selection count: "2 of 6 characters selected"
- Color coding: Red (insufficient), yellow (minimum met), green (optimal range)

### Confirm Selection Button

#### Button States
- **Disabled**: When validation fails (< 2 or > 6 characters)
- **Enabled**: When 2-6 characters are selected
- **Loading**: During simulation initiation (if applicable)

#### Click Behavior
```javascript
const handleConfirmSelection = useCallback(async () => {
  if (!selectionValidation.isValid) {
    setValidationError(selectionValidation.message);
    return;
  }
  
  try {
    // Optional: Show confirmation dialog
    setShowConfirmDialog(true);
    
    // Prepare simulation data
    const simulationData = {
      character_names: selectedCharacters,
      turns: null, // Use default from config
      narrative_style: 'epic'
    };
    
    // Navigate to simulation or trigger simulation execution
    onSimulationStart(simulationData);
    
  } catch (error) {
    setError('Failed to start simulation. Please try again.');
  }
}, [selectedCharacters, selectionValidation, onSimulationStart]);
```

### Error Messaging for Invalid Selections
- **Display Location**: Below character grid, above confirm button
- **Error Types**: Validation errors, API errors, simulation start errors
- **Auto-dismiss**: Errors clear when user corrects the issue
- **Styling**: Clear visual distinction with appropriate color coding

## 5. Visual Layout

### Component Structure
```
CharacterSelectionComponent
├── Header Section
│   ├── Title: "Select Characters for Simulation"
│   ├── Subtitle: "Choose 2-6 characters for your Warhammer 40k scenario"
│   └── Selection Counter: "X of 6 characters selected"
├── Main Content Area
│   ├── Loading State (when isLoading = true)
│   │   ├── Loading Spinner
│   │   └── "Loading available characters..."
│   ├── Error State (when error exists)
│   │   ├── Error Icon
│   │   ├── Error Message
│   │   └── Retry Button
│   └── Character Grid (when data loaded)
│       └── Character Cards (responsive grid)
├── Validation Message Area
│   └── Error/Warning Messages
└── Footer Section
    ├── Confirm Selection Button
    └── Additional Actions (Cancel, Reset)
```

### Character Grid Layout
- **Desktop**: 3-column responsive grid (CSS Grid or Flexbox)
- **Tablet**: 2-column grid with larger cards
- **Mobile**: Single column, full-width cards
- **Spacing**: Consistent 16px gaps between cards
- **Container**: Max-width with center alignment

### Character Card Design
```
Character Card (200px × 280px recommended)
├── Character Preview Area (160px height)
│   ├── Character Image/Icon (placeholder for future)
│   ├── Selection Indicator (checkmark overlay)
│   └── Character Name (overlay text)
├── Character Info Section (120px height)
│   ├── Character Name (title)
│   ├── Faction Information
│   ├── Brief Description (truncated)
│   └── "View Details" link (optional)
└── Selection Border (dynamic styling)
```

### Visual Design Specifications

#### Color Scheme (Warhammer 40k Theme)
- **Primary**: Dark Imperial Gold (#B8860B)
- **Secondary**: Deep Crimson (#8B0000)
- **Background**: Dark Steel (#2F2F2F)
- **Text**: Light Gray (#E0E0E0)
- **Accent**: Bright Gold (#FFD700)
- **Error**: Imperial Red (#CC0000)
- **Success**: Loyalist Green (#228B22)

#### Typography
- **Headers**: Bold, serif font (Cinzel or similar Imperial style)
- **Body Text**: Clean sans-serif (Inter, Roboto)
- **Character Names**: Medium weight, slightly larger size
- **Descriptions**: Regular weight, readable size

#### Interactive Elements
- **Hover Effects**: Subtle scale (1.02x) and shadow elevation
- **Selection State**: 3px solid border in accent color
- **Disabled State**: 50% opacity with grayscale filter
- **Focus States**: Clear outline for keyboard navigation

### Loading State Visual Indicators
- **Full Page Loading**: Centered spinner with "Loading characters..." text
- **Character Detail Loading**: Skeleton placeholder cards
- **Button Loading**: Spinner inside button with disabled state
- **Progress Indication**: Optional progress bar for multiple API calls

### Responsive Design Considerations
- **Breakpoints**: Mobile (< 768px), Tablet (768-1024px), Desktop (> 1024px)
- **Touch Targets**: Minimum 44px touch area for mobile
- **Text Scaling**: Readable font sizes across all devices
- **Performance**: Lazy loading for character details and images

### Accessibility Features
- **ARIA Labels**: Descriptive labels for all interactive elements
- **Keyboard Navigation**: Full keyboard support with logical tab order
- **Screen Reader Support**: Semantic HTML structure
- **Color Contrast**: WCAG AA compliant contrast ratios
- **Focus Management**: Clear focus indicators and logical flow

### Error Message Display Areas
- **Global Errors**: Top of component with dismiss functionality
- **Validation Errors**: Below character grid, above action buttons
- **Inline Errors**: Within relevant input areas or card contexts
- **Toast Notifications**: For temporary status messages

This comprehensive specification provides frontend developers with detailed requirements to implement a robust, user-friendly Character Selection Component that integrates seamlessly with the existing Warhammer 40k Multi-Agent Simulator architecture while maintaining excellent user experience and accessibility standards.

---

# Character Creation Component - UI Design Specification

## 1. Component Overview

The Character Creation Component serves as the sacred forge where new warriors are conceived through the divine union of user creativity and AI Scribe enhancement. This React-based interface channels the mystical powers of the Gemini API Master Context Engineer to transmute mere descriptions and lore fragments into fully realized character souls, ready to answer the Emperor's call in the grim darkness of the far future.

### Sacred Purpose
- Enable Tech-Adepts to craft new character entities through the blessed AI Scribe ritual
- Provide intuitive interface for character description input and contextual file uploads
- Integrate seamlessly with the enhanced POST /characters endpoint for multipart/form-data transmission
- Guide users through the character creation workflow with appropriate Imperial guidance
- Ensure successful character manifestation and automatic return to Character Selection sanctum

### Role in the Greater Machine
1. **Genesis Gate**: Entry point for birthing new character entities into the simulation realm
2. **AI Scribe Conduit**: Interface for invoking Gemini API enhancement protocols
3. **File Processing Altar**: Sacred space for uploading contextual lore files
4. **Validation Shrine**: Ensures all inputs meet the strict codex requirements
5. **Workflow Orchestrator**: Manages the complete character creation cycle from conception to manifestation

### Context within Novel Engine Omnissiah
The component integrates with the existing React frontend (blessed with React 19 + Vite sacred technologies) and communes with the FastAPI backend through the enhanced POST /characters endpoint. It serves as the creative nexus between human inspiration and machine precision, leveraging the AI Scribe enhancement system to generate comprehensive character codex entries.

## 2. Component Layout Architecture

The Character Creation Component follows the sacred geometry of the Omnissiah, arranged in three primary consecrated zones:

### Sacred Input Sanctum
```
Character Creation Interface (Full viewport utilization)
├── Header Shrine
│   ├── Sacred Title: "Forge New Character Soul"
│   ├── Blessed Subtitle: "Invoke AI Scribe Enhancement to Create Your Warrior"
│   └── Progress Indicator: Creation workflow status
├── Primary Input Altar (Central focus)
│   ├── Character Name Field
│   │   ├── Input Label: "Character's Sacred Designation"
│   │   ├── Validation Requirements: 3-50 characters, alphanumeric + underscores
│   │   └── Real-time validation feedback
│   ├── Character Description Area (Large text area)
│   │   ├── Input Label: "Character's Narrative Genesis"
│   │   ├── Dimensions: Minimum 4 rows, expandable to 12 rows
│   │   ├── Character Counter: Live count with 10-2000 character limits
│   │   ├── Placeholder Text: "Describe your character's origins, personality, appearance, and role in the 40k universe..."
│   │   └── Rich text formatting hints
│   └── Lore Files Upload Sanctum
│       ├── Upload Zone: "Upload Contextual Lore Files"
│       ├── Drag & Drop Area: Visual drop zone with Imperial iconography
│       ├── File Browser Button: "Select Lore Archives"
│       ├── Accepted Formats: .md, .txt, .yaml, .json
│       ├── File List Display: Show uploaded files with remove capability
│       └── Upload Progress Indicators: Per-file upload status
└── Action Command Center
    ├── Forge Character Soul Button (Primary CTA)
    ├── Cancel/Return Button (Secondary action)
    └── Reset Form Button (Tertiary action)
```

### Layout Specifications

#### Character Description Text Area
- **Minimum Dimensions**: 400px width × 120px height (4 rows)
- **Maximum Dimensions**: 100% width × 360px height (12 rows)
- **Auto-resize**: Expands vertically based on content up to maximum
- **Styling**: Dark Imperial theme with golden accent borders
- **Placeholder Guidance**: "In the grim darkness of the far future, describe your character's origins, combat role, personality traits, and place within the Imperium. Include physical appearance, notable equipment, and any defining events that shaped their purpose..."

#### File Upload Zone
- **Layout**: Horizontal layout with drag-drop area and file list
- **Drag Zone Dimensions**: 300px width × 120px height minimum
- **Visual Indicators**: Dotted border, upload icon, instructional text
- **File List**: Vertical list showing filename, size, type, remove button
- **Multiple File Support**: Allow 1-5 files maximum, cumulative size limit 10MB

#### Sacred Forge Button
- **Dimensions**: 200px width × 48px height
- **Primary Styling**: Imperial Gold gradient with Aquila iconography
- **Loading State**: Spinning cogitator icon with sacred text animation
- **Disabled State**: When validation fails or during processing

## 3. API Interaction Protocol

### Primary Endpoint Integration

#### POST /characters - Sacred Character Creation Ritual
**Endpoint**: `http://localhost:8000/characters`
**Method**: POST
**Content-Type**: multipart/form-data

**Request Payload Structure**:
```javascript
const formData = new FormData();

// Character designation (required)
formData.append('name', characterName.trim().toLowerCase());

// Narrative description (required)
formData.append('description', characterDescription.trim());

// Optional contextual lore files
uploadedFiles.forEach((file, index) => {
  formData.append('files', file);
});
```

**Expected Response Format**:
```json
{
  "name": "new_warrior",
  "status": "ai_scribe_enhanced_complete",
  "ai_scribe_enhanced": true,
  "files_processed": 2
}
```

### API Implementation Pattern

```javascript
// API call configuration
const API_BASE_URL = 'http://localhost:8000';
const CHARACTER_CREATION_TIMEOUT = 60000; // 60 seconds for AI Scribe processing

const createCharacterWithAIScribe = async (characterData) => {
  try {
    setIsForging(true);
    setForgingProgress('Preparing sacred ritual...');
    
    // Prepare multipart form data
    const formData = new FormData();
    formData.append('name', characterData.name);
    formData.append('description', characterData.description);
    
    // Append lore files if provided
    characterData.files.forEach(file => {
      formData.append('files', file);
    });
    
    setForgingProgress('Invoking AI Scribe enhancement...');
    
    const response = await axios.post(
      `${API_BASE_URL}/characters`,
      formData,
      {
        timeout: CHARACTER_CREATION_TIMEOUT,
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(percentCompleted);
        }
      }
    );
    
    setForgingProgress('Character soul forged successfully!');
    return response.data;
    
  } catch (error) {
    logger.error('Character creation failed:', error);
    
    if (error.code === 'ECONNABORTED') {
      throw new Error('AI Scribe ritual timeout - The machine spirits require more time');
    } else if (error.response?.status === 400) {
      throw new Error(`Validation failure: ${error.response.data.detail}`);
    } else if (error.response?.status === 409) {
      throw new Error('Character designation already exists in the Codex');
    } else if (error.response?.status === 500) {
      throw new Error('AI Scribe enhancement failed - The Omnissiah tests our resolve');
    } else {
      throw new Error('Sacred connection to the forge severed - Ensure the Machine God\'s blessing');
    }
  } finally {
    setIsForging(false);
    setUploadProgress(0);
  }
};
```

### Multipart Form Data Best Practices

#### File Validation Protocol
```javascript
const validateLoreFiles = (files) => {
  const allowedTypes = ['.md', '.txt', '.yaml', '.yml', '.json'];
  const maxFileSize = 2 * 1024 * 1024; // 2MB per file
  const maxTotalSize = 10 * 1024 * 1024; // 10MB total
  
  let totalSize = 0;
  const validationErrors = [];
  
  files.forEach((file, index) => {
    totalSize += file.size;
    
    // Check file type
    const fileExt = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    if (!allowedTypes.includes(fileExt)) {
      validationErrors.push(`File ${index + 1}: Unsupported format ${fileExt}`);
    }
    
    // Check individual file size
    if (file.size > maxFileSize) {
      validationErrors.push(`File ${index + 1}: Size exceeds 2MB limit`);
    }
  });
  
  // Check total size
  if (totalSize > maxTotalSize) {
    validationErrors.push('Total file size exceeds 10MB limit');
  }
  
  return {
    isValid: validationErrors.length === 0,
    errors: validationErrors,
    totalSize
  };
};
```

## 4. User Feedback & Experience Protocol

### Loading State Management - The Sacred Cogitator Ritual

#### Primary Loading States
1. **File Upload Progress**: Individual file upload with progress bars
2. **AI Scribe Invocation**: Sacred spinning cogitator with Mechanicus prayers
3. **Character Manifestation**: Final processing with completion countdown

#### Loading State Implementation
```javascript
const [forgingState, setForgingState] = useState({
  isForging: false,
  currentPhase: null,
  progress: 0,
  sacredText: ''
});

const forgingPhases = [
  {
    phase: 'preparation',
    text: 'Preparing sacred oils and incense...',
    duration: 2000
  },
  {
    phase: 'invocation',
    text: 'Invoking the AI Scribe protocols...',
    duration: 15000
  },
  {
    phase: 'enhancement',
    text: 'Channeling Gemini API enhancement...',
    duration: 20000
  },
  {
    phase: 'manifestation',
    text: 'Manifesting character soul in the digital realm...',
    duration: 8000
  },
  {
    phase: 'completion',
    text: 'Character successfully forged! The Omnissiah is pleased.',
    duration: 3000
  }
];
```

#### Sacred Loading Animation
```css
.cogitator-spinner {
  animation: sanctified-rotation 2s linear infinite;
  width: 48px;
  height: 48px;
  background: radial-gradient(circle, #FFD700, #B8860B);
  border-radius: 50%;
  position: relative;
}

.cogitator-spinner::before {
  content: '⚙';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 24px;
  color: #2F2F2F;
}

@keyframes sanctified-rotation {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.mechanicus-prayer {
  font-family: 'Cinzel', serif;
  font-style: italic;
  color: #B8860B;
  text-align: center;
  margin-top: 16px;
  opacity: 0.9;
}
```

### Success & Error Messaging Protocol

#### Success State Handling
```javascript
const handleCreationSuccess = (response) => {
  const successMessage = `Character "${response.name}" successfully forged!`;
  const enhancementStatus = response.ai_scribe_enhanced 
    ? `AI Scribe enhancement: COMPLETE (${response.files_processed} files processed)`
    : 'Basic character template created';
  
  setNotification({
    type: 'success',
    title: 'Sacred Forge Complete',
    message: successMessage,
    detail: enhancementStatus,
    autoClose: 5000
  });
  
  // Automatic redirection after brief success display
  setTimeout(() => {
    navigateToCharacterSelection();
  }, 2000);
};
```

#### Error State Classifications
1. **Validation Errors**: Input requirements not met
2. **Network Errors**: Connection or timeout issues
3. **Server Errors**: API processing failures
4. **File Processing Errors**: Upload or format issues

#### Error Message Templates
```javascript
const errorMessages = {
  validation: {
    nameLength: 'Character designation must be 3-50 characters',
    nameFormat: 'Only alphanumeric characters and underscores permitted',
    descriptionLength: 'Description must be 10-2000 characters',
    fileFormat: 'Only .md, .txt, .yaml, and .json files accepted',
    fileSize: 'Individual files must not exceed 2MB',
    totalSize: 'Total upload size must not exceed 10MB'
  },
  network: {
    timeout: 'AI Scribe ritual interrupted - The machine spirits require patience',
    connection: 'Sacred connection severed - Ensure the server\'s benediction',
    server: 'The Omnissiah tests our resolve - Server experiencing difficulties'
  },
  creation: {
    duplicate: 'Character designation already exists in the sacred Codex',
    processing: 'AI Scribe enhancement failed - The knowledge may be corrupted',
    unknown: 'Unforeseen complications in the forging process'
  }
};
```

### Progress Indication System

#### Multi-Stage Progress Display
```javascript
const ProgressIndicator = ({ currentPhase, progress }) => (
  <div className="forging-progress">
    <div className="progress-header">
      <h3>Sacred Forging Progress</h3>
      <span className="progress-percentage">{progress}%</span>
    </div>
    
    <div className="progress-bar-container">
      <div 
        className="progress-bar" 
        style={{ width: `${progress}%` }}
      />
    </div>
    
    <div className="phase-indicators">
      {forgingPhases.map((phase, index) => (
        <div 
          key={phase.phase}
          className={`phase-indicator ${
            currentPhase === phase.phase ? 'active' : 
            index < getCurrentPhaseIndex() ? 'completed' : 'pending'
          }`}
        >
          <div className="phase-icon">
            {index < getCurrentPhaseIndex() ? '✓' : 
             currentPhase === phase.phase ? '⚙' : '○'}
          </div>
          <span className="phase-label">{phase.text}</span>
        </div>
      ))}
    </div>
  </div>
);
```

## 5. Workflow Management

### Complete User Journey Protocol

#### Stage 1: Initial Interface Presentation
```javascript
const CharacterCreationComponent = () => {
  useEffect(() => {
    // Initialize component with proper blessing
    logEvent('character_creation_accessed');
    resetFormState();
    setCurrentStep('input');
  }, []);

  return (
    <div className="character-creation-sanctum">
      {currentStep === 'input' && <InputInterface />}
      {currentStep === 'forging' && <ForgingRitual />}
      {currentStep === 'completion' && <CompletionCeremony />}
    </div>
  );
};
```

#### Stage 2: Input Validation & Processing
```javascript
const validateAndSubmit = async () => {
  // Pre-flight validation checks
  const nameValidation = validateCharacterName(characterName);
  const descriptionValidation = validateDescription(characterDescription);
  const fileValidation = validateLoreFiles(uploadedFiles);
  
  if (!nameValidation.isValid) {
    setFieldError('name', nameValidation.message);
    return;
  }
  
  if (!descriptionValidation.isValid) {
    setFieldError('description', descriptionValidation.message);
    return;
  }
  
  if (!fileValidation.isValid) {
    setFieldError('files', fileValidation.errors.join(', '));
    return;
  }
  
  // Proceed with sacred forging ritual
  setCurrentStep('forging');
  await initiateCharacterCreation();
};
```

#### Stage 3: Forging Ritual Execution
```javascript
const initiateCharacterCreation = async () => {
  try {
    const characterData = {
      name: characterName,
      description: characterDescription,
      files: uploadedFiles
    };
    
    const response = await createCharacterWithAIScribe(characterData);
    
    setCreationResult(response);
    setCurrentStep('completion');
    
  } catch (error) {
    setCurrentStep('input');
    setGlobalError(error.message);
  }
};
```

#### Stage 4: Success Handling & Navigation
```javascript
const CompletionCeremony = () => {
  useEffect(() => {
    const timer = setTimeout(() => {
      // Log successful creation
      logEvent('character_created', {
        name: creationResult.name,
        ai_enhanced: creationResult.ai_scribe_enhanced,
        files_processed: creationResult.files_processed
      });
      
      // Navigate back to Character Selection
      navigate('/character-selection', { 
        state: { 
          newCharacter: creationResult.name,
          showWelcome: true 
        }
      });
    }, 3000);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="completion-ceremony">
      <div className="success-icon">⚡</div>
      <h2>Character Soul Successfully Forged!</h2>
      <p>The Omnissiah blesses "{creationResult.name}"</p>
      <p>Returning to Character Selection in 3 seconds...</p>
    </div>
  );
};
```

### Auto-Navigation Protocol

#### Character Selection Return Logic
```javascript
const navigateToCharacterSelection = () => {
  // Clear any temporary state
  clearCreationForm();
  
  // Navigate with success state
  navigate('/character-selection', {
    state: {
      newCharacterCreated: creationResult.name,
      showSuccessNotification: true,
      autoSelectNew: true
    },
    replace: true // Replace current route to prevent back navigation to creation form
  });
};

// In Character Selection Component - handle return from creation
const CharacterSelection = () => {
  const location = useLocation();
  
  useEffect(() => {
    if (location.state?.newCharacterCreated) {
      // Show success notification
      showNotification({
        type: 'success',
        message: `New character "${location.state.newCharacterCreated}" added to your roster!`
      });
      
      // Auto-select the newly created character
      if (location.state.autoSelectNew) {
        setSelectedCharacters([location.state.newCharacterCreated]);
      }
      
      // Clear the navigation state
      window.history.replaceState(null, '');
    }
  }, [location]);
};
```

### Error Recovery Workflow

#### Retry Mechanism Implementation
```javascript
const RetryInterface = ({ error, onRetry, onCancel }) => (
  <div className="error-recovery-shrine">
    <div className="error-icon">⚠</div>
    <h3>Sacred Ritual Interrupted</h3>
    <p className="error-message">{error}</p>
    
    <div className="recovery-actions">
      <button 
        className="retry-button primary"
        onClick={onRetry}
      >
        Retry Sacred Forging
      </button>
      <button 
        className="cancel-button secondary"
        onClick={onCancel}
      >
        Return to Input Sanctum
      </button>
    </div>
    
    <div className="tech-priest-guidance">
      <p><em>"Even the mightiest machines require patience and persistence. The Omnissiah tests our dedication through temporary setbacks."</em></p>
    </div>
  </div>
);
```

This sacred specification provides the complete architectural blueprint for implementing the Character Creation Component, ensuring seamless integration with the AI Scribe enhancement system while maintaining the blessed user experience standards of the Omnissiah's digital realm.