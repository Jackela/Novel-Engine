#!/bin/bash

# StoryForge AI - One-Click Setup Script
# This script automates the complete setup process for both technical and non-technical users

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Emoji for better UX
CHECKMARK="✅"
CROSSMARK="❌"
ROCKET="🚀"
GEAR="⚙️"
BOOK="📚"

echo -e "${BLUE}${ROCKET} StoryForge AI - One-Click Setup${NC}"
echo "=========================================="
echo ""

# Function to print status messages
print_status() {
    echo -e "${BLUE}${GEAR} $1${NC}"
}

print_success() {
    echo -e "${GREEN}${CHECKMARK} $1${NC}"
}

print_error() {
    echo -e "${RED}${CROSSMARK} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3.8+ is required but not found"
    echo "Please install Python from https://python.org/downloads/"
    exit 1
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
else
    print_error "Node.js 16+ is required but not found"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check npm
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: $NPM_VERSION"
else
    print_error "npm is required but not found"
    echo "Please install npm (usually comes with Node.js)"
    exit 1
fi

# Check pip
if command_exists pip3 || command_exists pip; then
    if command_exists pip3; then
        PIP_CMD="pip3"
    else
        PIP_CMD="pip"
    fi
    print_success "pip found"
else
    print_error "pip is required but not found"
    echo "Please install pip: python -m ensurepip --upgrade"
    exit 1
fi

echo ""
print_status "Installing backend dependencies..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate || source venv/Scripts/activate 2>/dev/null || {
    print_error "Failed to activate virtual environment"
    exit 1
}

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    print_status "Installing Python packages from requirements.txt..."
    pip install -r requirements.txt
    print_success "Python dependencies installed"
else
    print_status "Installing core Python packages..."
    pip install fastapi uvicorn pyyaml requests python-multipart
    print_success "Core Python packages installed"
fi

echo ""
print_status "Setting up frontend..."

# Navigate to frontend directory
if [ -d "frontend" ]; then
    cd frontend
    
    # Install Node.js dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    print_success "Node.js dependencies installed"
    
    # Build frontend for production
    print_status "Building frontend for production..."
    npm run build
    print_success "Frontend built successfully"
    
    cd ..
else
    print_warning "Frontend directory not found, skipping frontend setup"
fi

echo ""
print_status "Creating configuration files..."

# Create environment example file
cat > .env.example << 'EOF'
# StoryForge AI Configuration
# Copy this file to .env and fill in your values

# Gemini API Key (Optional - for enhanced AI features)
# Get your key from: https://aistudio.google.com/
GEMINI_API_KEY=your_gemini_api_key_here

# Server Configuration
STORYFORGE_HOST=localhost
STORYFORGE_PORT=8000
STORYFORGE_FRONTEND_PORT=5173

# Story Generation Settings
STORYFORGE_DEFAULT_TURNS=3
STORYFORGE_NARRATIVE_STYLE=grimdark_dramatic

# Performance Settings
STORYFORGE_API_TIMEOUT=30
STORYFORGE_LOGGING_LEVEL=INFO
EOF

print_success "Environment configuration template created (.env.example)"

# Create startup script
cat > start.sh << 'EOF'
#!/bin/bash

# StoryForge AI - Startup Script
# Starts both backend and frontend servers

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting StoryForge AI...${NC}"
echo ""

# Load environment variables if .env file exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${GREEN}✅ Environment variables loaded${NC}"
fi

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    source venv/bin/activate || source venv/Scripts/activate
    echo -e "${GREEN}✅ Python virtual environment activated${NC}"
fi

# Start backend server
echo -e "${BLUE}📡 Starting backend server...${NC}"
python api_server.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Check if backend is running
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Backend server started (PID: $BACKEND_PID)${NC}"
    echo -e "${GREEN}🌐 Backend available at: http://localhost:8000${NC}"
else
    echo -e "\033[0;31m❌ Failed to start backend server${NC}"
    exit 1
fi

# Start frontend if directory exists
if [ -d "frontend" ]; then
    echo -e "${BLUE}🎨 Starting frontend server...${NC}"
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    
    # Wait a moment for frontend to start
    sleep 3
    
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Frontend server started (PID: $FRONTEND_PID)${NC}"
        echo -e "${GREEN}🌐 Frontend available at: http://localhost:5173${NC}"
    else
        echo -e "\033[1;33m⚠️  Frontend server may have failed to start${NC}"
    fi
fi

echo ""
echo -e "${GREEN}🎉 StoryForge AI is now running!${NC}"
echo ""
echo "📖 Quick Start Guide:"
echo "1. Open your browser to: http://localhost:5173"
echo "2. Follow the setup wizard to configure your API key (optional)"
echo "3. Create your first story!"
echo ""
echo "📚 Documentation: Check README.md for detailed usage"
echo "🔧 Configuration: Edit .env file for custom settings"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${BLUE}🛑 Stopping services...${NC}"
    
    # Kill backend
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo -e "${GREEN}✅ Backend server stopped${NC}"
    fi
    
    # Kill frontend
    if [ ! -z "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo -e "${GREEN}✅ Frontend server stopped${NC}"
    fi
    
    echo -e "${GREEN}👋 StoryForge AI stopped. Thank you for using our system!${NC}"
}

# Set up cleanup on script exit
trap cleanup EXIT

# Wait for user interrupt
wait
EOF

# Make startup script executable
chmod +x start.sh
print_success "Startup script created (start.sh)"

# Create development script
cat > dev.sh << 'EOF'
#!/bin/bash

# StoryForge AI - Development Script
# Starts servers in development mode with hot reload

set -e

echo "🔧 Starting StoryForge AI in development mode..."

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate || source venv/Scripts/activate
fi

# Start backend with auto-reload
echo "📡 Starting backend with auto-reload..."
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend in development mode
if [ -d "frontend" ]; then
    echo "🎨 Starting frontend in development mode..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
fi

echo ""
echo "🎉 Development servers running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop"

# Cleanup function
cleanup() {
    echo "Stopping development servers..."
    kill $BACKEND_PID 2>/dev/null || true
    [ ! -z "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null || true
}

trap cleanup EXIT
wait
EOF

chmod +x dev.sh
print_success "Development script created (dev.sh)"

echo ""
print_status "Running system health check..."

# Test Python imports
python3 -c "
try:
    import fastapi, uvicorn, yaml, requests
    print('✅ All Python dependencies available')
except ImportError as e:
    print(f'❌ Missing Python dependency: {e}')
    exit(1)
" || {
    print_error "Python dependency check failed"
    exit 1
}

# Test Node.js setup if frontend exists
if [ -d "frontend" ]; then
    cd frontend
    if [ -f "package.json" ]; then
        print_success "Frontend package.json found"
    else
        print_warning "Frontend package.json not found"
    fi
    cd ..
fi

echo ""
echo -e "${GREEN}${CHECKMARK}${CHECKMARK}${CHECKMARK} Setup Complete! ${CHECKMARK}${CHECKMARK}${CHECKMARK}${NC}"
echo ""
echo -e "${BLUE}${ROCKET} Next Steps:${NC}"
echo ""
echo "1. 🔑 Configure API Key (Optional but recommended):"
echo "   - Copy .env.example to .env"
echo "   - Get Gemini API key from: https://aistudio.google.com/"
echo "   - Add your key to the .env file"
echo ""
echo "2. 🚀 Start StoryForge AI:"
echo "   ./start.sh"
echo ""
echo "3. 🌐 Open your browser to:"
echo "   http://localhost:5173"
echo ""
echo "4. 📖 Follow the onboarding wizard to create your first story!"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "- Use ./dev.sh for development with hot reload"
echo "- Check README.md for detailed documentation"
echo "- The system works without API key but with limited AI features"
echo ""
echo -e "${GREEN}🎉 Welcome to StoryForge AI! ${BOOK} Happy storytelling!${NC}"