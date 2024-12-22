#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
CONFIG_FILE="$PROJECT_ROOT/config.json"

# Function to check if Python 3.8+ is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if (( $(echo "$PYTHON_VERSION < 3.8" | bc -l) )); then
        echo -e "${RED}Python 3.8 or higher is required. Current version: $PYTHON_VERSION${NC}"
        exit 1
    fi
}

# Function to create and activate virtual environment
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${BLUE}Creating virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Install requirements
    echo -e "${BLUE}Installing required packages...${NC}"
    pip install langchain langchain-anthropic python-dotenv
}

# Function to setup project structure
setup_project_structure() {
    mkdir -p "$PROJECT_ROOT/project_states"
    mkdir -p "$PROJECT_ROOT/agent_memories"
    
    # Create .env file if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo -e "${YELLOW}Creating .env file...${NC}"
        read -p "Enter your Anthropic API key: " api_key
        echo "ANTHROPIC_API_KEY=$api_key" > "$PROJECT_ROOT/.env"
    fi
}

# Function to list all projects
list_projects() {
    echo -e "${BLUE}Available projects:${NC}"
    if [ -d "$PROJECT_ROOT/project_states" ]; then
        projects=$(ls "$PROJECT_ROOT/project_states" | grep '.json' | sed 's/.json//')
        if [ -z "$projects" ]; then
            echo "No projects found."
        else
            echo "$projects" | nl
        fi
    else
        echo "No projects directory found."
    fi
}

# Function to create a new project
create_project() {
    echo -e "${BLUE}Creating new project${NC}"
    read -p "Enter project name: " project_name
    
    # Replace spaces with underscores and convert to lowercase
    project_id=$(echo "$project_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
    
    echo "Enter project requirements (press Ctrl+D when done):"
    requirements=$(cat)
    
    # Create Python script to start project
    temp_script=$(mktemp)
    cat > "$temp_script" << EOL
import asyncio
import json
from software_team import SoftwareTeam

async def main():
    team = SoftwareTeam("$project_id")
    await team.start_new_project("$project_name", """$requirements""")
    print(json.dumps({"status": "success"}))

if __name__ == "__main__":
    asyncio.run(main())
EOL
    
    python "$temp_script"
    rm "$temp_script"
    
    echo -e "${GREEN}Project '$project_name' created successfully!${NC}"
}

# Function to resume existing project
resume_project() {
    list_projects
    read -p "Enter project number to resume: " project_num
    
    # Get project ID from number
    project_id=$(ls "$PROJECT_ROOT/project_states" | grep '.json' | sed 's/.json//' | sed -n "${project_num}p")
    
    if [ -z "$project_id" ]; then
        echo -e "${RED}Invalid project number${NC}"
        return 1
    fi
    
    # Create Python script to resume project
    temp_script=$(mktemp)
    cat > "$temp_script" << EOL
import asyncio
from software_team import SoftwareTeam

async def main():
    team = SoftwareTeam("$project_id")
    await team.resume_project()

if __name__ == "__main__":
    asyncio.run(main())
EOL
    
    python "$temp_script"
    rm "$temp_script"
}

# Function to add milestone to project
add_milestone() {
    list_projects
    read -p "Enter project number to add milestone: " project_num
    
    # Get project ID from number
    project_id=$(ls "$PROJECT_ROOT/project_states" | grep '.json' | sed 's/.json//' | sed -n "${project_num}p")
    
    if [ -z "$project_id" ]; then
        echo -e "${RED}Invalid project number${NC}"
        return 1
    fi
    
    echo "Enter milestone description (press Ctrl+D when done):"
    milestone=$(cat)
    
    # Create Python script to add milestone
    temp_script=$(mktemp)
    cat > "$temp_script" << EOL
import asyncio
import json
from software_team import SoftwareTeam

async def main():
    team = SoftwareTeam("$project_id")
    results = await team.process_milestone("""$milestone""")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
EOL
    
    python "$temp_script"
    rm "$temp_script"
}

# Function to show project status
show_status() {
    list_projects
    read -p "Enter project number to show status: " project_num
    
    # Get project ID from number
    project_id=$(ls "$PROJECT_ROOT/project_states" | grep '.json' | sed -n "${project_num}p")
    
    if [ -z "$project_id" ]; then
        echo -e "${RED}Invalid project number${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Project Status:${NC}"
    cat "$PROJECT_ROOT/project_states/$project_id"
}

# Function to show agent memory
show_agent_memory() {
    list_projects
    read -p "Enter project number: " project_num
    
    # Get project ID from number
    project_id=$(ls "$PROJECT_ROOT/project_states" | grep '.json' | sed 's/.json//' | sed -n "${project_num}p")
    
    if [ -z "$project_id" ]; then
        echo -e "${RED}Invalid project number${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Select agent:${NC}"
    select agent in "CEO" "CTO" "Tester" "Coder"; do
        if [ -n "$agent" ]; then
            memory_file="$PROJECT_ROOT/agent_memories/$project_id/${agent}.json"
            if [ -f "$memory_file" ]; then
                echo -e "${BLUE}${agent}'s Memory:${NC}"
                cat "$memory_file"
            else
                echo -e "${RED}No memory file found for ${agent}${NC}"
            fi
            break
        fi
    done
}

# Main menu
main_menu() {
    while true; do
        echo -e "\n${BLUE}Software Team Project Manager${NC}"
        echo "1. Create new project"
        echo "2. Resume existing project"
        echo "3. Add milestone to project"
        echo "4. Show project status"
        echo "5. Show agent memory"
        echo "6. List all projects"
        echo "7. Exit"
        
        read -p "Select an option: " choice
        
        case $choice in
            1) create_project ;;
            2) resume_project ;;
            3) add_milestone ;;
            4) show_status ;;
            5) show_agent_memory ;;
            6) list_projects ;;
            7) 
                echo -e "${GREEN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option${NC}"
                ;;
        esac
    done
}

# Script initialization
echo -e "${BLUE}Initializing Software Team Project Manager...${NC}"

# Check requirements
check_python

# Setup virtual environment
setup_venv

# Setup project structure
setup_project_structure

# Start main menu
main_menu
