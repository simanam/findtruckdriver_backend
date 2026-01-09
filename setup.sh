#!/bin/bash
# Initial setup script for Find a Truck Driver backend

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚛 Find a Truck Driver - Backend Setup${NC}"
echo ""

# Step 1: Create virtual environment
echo -e "${BLUE}Step 1/4: Creating virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment already exists. Skipping...${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi
echo ""

# Step 2: Activate and upgrade pip
echo -e "${BLUE}Step 2/4: Activating environment and upgrading pip...${NC}"
source venv/bin/activate
pip install --upgrade pip --quiet
echo -e "${GREEN}✅ Pip upgraded${NC}"
echo ""

# Step 3: Install dependencies
echo -e "${BLUE}Step 3/4: Installing dependencies...${NC}"
echo -e "${YELLOW}This may take 2-3 minutes...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Step 4: Check .env file
echo -e "${BLUE}Step 4/4: Checking configuration...${NC}"
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env file found${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env file with your Supabase credentials!${NC}"
fi
echo ""

# Step 5: Create logs directory
if [ ! -d "logs" ]; then
    mkdir -p logs
    echo -e "${GREEN}✅ Logs directory created${NC}"
fi
echo ""

# Done
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Edit .env file with your Supabase credentials:"
echo -e "     ${YELLOW}nano .env${NC}"
echo ""
echo -e "  2. Run the development server:"
echo -e "     ${YELLOW}./run_dev.sh${NC}"
echo ""
echo -e "  3. Visit the API docs:"
echo -e "     ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
