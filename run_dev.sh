#!/bin/bash
# Development server startup script

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚛 Find a Truck Driver - Backend Development Server${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Dependencies not installed. Installing...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo -e "${YELLOW}Please create .env file from .env.example:${NC}"
    echo "  cp .env.example .env"
    echo "  # Then edit .env with your Supabase credentials"
    exit 1
fi

# Check if logs directory exists
if [ ! -d "logs" ]; then
    mkdir -p logs
fi

echo -e "${GREEN}✅ Environment ready${NC}"
echo ""
echo -e "${BLUE}🚀 Starting FastAPI server...${NC}"
echo -e "${YELLOW}📖 API Docs will be available at: http://localhost:8000/docs${NC}"
echo -e "${YELLOW}🏥 Health check at: http://localhost:8000/health${NC}"
echo ""
echo -e "${BLUE}Press CTRL+C to stop the server${NC}"
echo ""

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
