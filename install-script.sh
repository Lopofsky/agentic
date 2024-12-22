#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Installing Software Team Project Manager...${NC}"

# Create project directory
PROJECT_DIR="software_team_project"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Download project manager script
echo -e "${BLUE}Downloading project manager script...${NC}"
curl -o project_manager.sh https://raw.githubusercontent.com/your-repo/software-team/main/project_manager.sh
chmod +x project_manager.sh

# Download main Python script
echo -e "${BLUE}Downloading Python implementation...${NC}"
curl -o software_team.py https://raw.githubusercontent.com/your-repo/software-team/main/software_team.py

# Create required directories
mkdir -p project_states
mkdir -p agent_memories

echo -e "${GREEN}Installation complete!${NC}"
echo -e "To start the project manager, run: ${BLUE}./project_manager.sh${NC}"
