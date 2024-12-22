import os
import json
import asyncio
import datetime
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ProjectStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    REVIEWING = "reviewing"
    TESTING = "testing"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"

@dataclass
class Milestone:
    id: str
    description: str
    status: ProjectStatus
    assigned_to: str
    created_at: str
    completed_at: Optional[str] = None
    feedback: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.feedback is None:
            self.feedback = []

@dataclass
class ProjectState:
    project_id: str
    name: str
    requirements: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    milestones: List[Milestone]
    learning_points: List[Dict[str, str]]
    team_feedback: Dict[str, List[Dict[str, str]]]
    current_milestone_id: Optional[str]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectState':
        data['milestones'] = [Milestone(**m) for m in data['milestones']]
        return cls(**data)

class ProjectStateManager:
    def __init__(self, project_dir: str = "project_states"):
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(exist_ok=True)
        
    def save_state(self, state: ProjectState) -> None:
        """Save project state to disk"""
        file_path = self.project_dir / f"{state.project_id}.json"
        with open(file_path, 'w') as f:
            json.dump(state.to_dict(), f, indent=2)
            
    def load_state(self, project_id: str) -> Optional[ProjectState]:
        """Load project state from disk"""
        file_path = self.project_dir / f"{project_id}.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
                return ProjectState.from_dict(data)
        return None
    
    def list_projects(self) -> List[str]:
        """List all project IDs"""
        return [f.stem for f in self.project_dir.glob("*.json")]

class AgentMemory:
    def __init__(self, agent_id: str, project_id: str):
        self.memory_file = Path(f"agent_memories/{project_id}/{agent_id}.json")
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_memory()
        
    def load_memory(self) -> None:
        """Load agent's memory from disk"""
        if self.memory_file.exists():
            with open(self.memory_file, 'r') as f:
                self.memory = json.load(f)
        else:
            self.memory = {
                "decisions": [],
                "learnings": [],
                "context": {},
                "next_steps": []
            }
            
    def save_memory(self) -> None:
        """Save agent's memory to disk"""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)
            
    def add_decision(self, decision: str, context: Dict[str, Any]) -> None:
        """Record a decision with context"""
        self.memory["decisions"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "decision": decision,
            "context": context
        })
        self.save_memory()
        
    def add_learning(self, learning: str) -> None:
        """Record a learning point"""
        self.memory["learnings"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "learning": learning
        })
        self.save_memory()
        
    def update_context(self, context: Dict[str, Any]) -> None:
        """Update agent's context"""
        self.memory["context"].update(context)
        self.save_memory()
        
    def set_next_steps(self, steps: List[str]) -> None:
        """Set next steps for the agent"""
        self.memory["next_steps"] = steps
        self.save_memory()
        
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of agent's memory"""
        return {
            "recent_decisions": self.memory["decisions"][-5:],
            "key_learnings": self.memory["learnings"][-5:],
            "current_context": self.memory["context"],
            "pending_steps": self.memory["next_steps"]
        }

class SoftwareTeamAgent:
    def __init__(
        self,
        role: str,
        llm: ChatAnthropic,
        project_id: str,
        memory: Optional[AgentMemory] = None
    ) -> None:
        self.role = role
        self.llm = llm
        self.project_id = project_id
        self.memory = memory or AgentMemory(role, project_id)
        self.system_prompts = {
            "CEO": """You are the CEO of a software company. Your role is to:
                     - Understand and maintain project vision and business goals
                     - Track project progress and alignment with objectives
                     - Document key decisions and rationale
                     - Ensure continuous value delivery""",
            
            "CTO": """You are the CTO of a software company. Your role is to:
                     - Maintain technical vision and architecture
                     - Track technical debt and architectural decisions
                     - Document technical learnings and improvements
                     - Ensure technical excellence and innovation""",
            
            "Tester": """You are the Quality Assurance Lead. Your role is to:
                        - Maintain test strategies and quality metrics
                        - Track test coverage and technical debt
                        - Document testing insights and improvements
                        - Ensure consistent quality standards""",
            
            "Coder": """You are the Senior Software Engineer. Your role is to:
                       - Maintain code quality and implementation standards
                       - Track technical challenges and solutions
                       - Document code decisions and improvements
                       - Ensure maintainable and efficient code"""
        }
        
    async def process_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        save_decision: bool = True
    ) -> str:
        """Process a message and optionally save the decision"""
        try:
            # Include memory summary in context
            memory_summary = self.memory.get_memory_summary()
            full_context = {
                **(context or {}),
                "memory_summary": memory_summary
            }
            
            messages = [
                SystemMessage(content=self.system_prompts[self.role]),
                HumanMessage(content=self._format_input(message, full_context))
            ]
            
            response = self.llm.generate([messages])
            response_text = response.generations[0][0].text
            
            if save_decision:
                self.memory.add_decision(response_text, full_context)
            
            return response_text
            
        except Exception as e:
            self.memory.add_learning(f"Error encountered: {str(e)}")
            raise RuntimeError(f"Error in {self.role} agent: {str(e)}")
            
    def _format_input(self, message: str, context: Dict[str, Any]) -> str:
        """Format input message with context and memory"""
        formatted_context = json.dumps(context, indent=2)
        return f"""Project Context:
{formatted_context}

Current Task:
{message}

Please provide your response considering the project history and current context.
Include any learnings or improvements for the project."""

class SoftwareTeam:
    def __init__(self, project_id: str) -> None:
        """Initialize the software team for a specific project"""
        self.project_id = project_id
        self.state_manager = ProjectStateManager()
        
        # Initialize LLM
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
            
        self.llm = ChatAnthropic(
            model="claude-3-sonnet-20240229",
            anthropic_api_key=api_key,
            temperature=0.7,
            max_tokens=4096
        )
        
        # Initialize agents with project-specific memory
        self.agents = {
            "CEO": SoftwareTeamAgent("CEO", self.llm, project_id),
            "CTO": SoftwareTeamAgent("CTO", self.llm, project_id),
            "Tester": SoftwareTeamAgent("Tester", self.llm, project_id),
            "Coder": SoftwareTeamAgent("Coder", self.llm, project_id)
        }
        
        # Load or create project state
        self.state = self.state_manager.load_state(project_id)
        
    async def start_new_project(self, name: str, requirements: str) -> None:
        """Start a new project with initial requirements"""
        timestamp = datetime.datetime.now().isoformat()
        
        self.state = ProjectState(
            project_id=self.project_id,
            name=name,
            requirements=requirements,
            status=ProjectStatus.NOT_STARTED,
            created_at=timestamp,
            updated_at=timestamp,
            milestones=[],
            learning_points=[],
            team_feedback={agent: [] for agent in self.agents.keys()},
            current_milestone_id=None
        )
        
        self.state_manager.save_state(self.state)
        
    async def resume_project(self) -> None:
        """Resume an existing project"""
        if not self.state:
            raise ValueError("No project state found. Please start a new project.")
            
        # Update agents with current project context
        for agent in self.agents.values():
            await agent.process_message(
                "Review project state and provide next steps.",
                {"project_state": self.state.to_dict()},
                save_decision=True
            )
            
    async def process_milestone(self, milestone_description: str) -> Dict[str, str]:
        """Process a single milestone through the team"""
        if not self.state:
            raise ValueError("No project state found")
            
        # Create new milestone
        milestone_id = f"milestone_{len(self.state.milestones) + 1}"
        milestone = Milestone(
            id=milestone_id,
            description=milestone_description,
            status=ProjectStatus.IN_PROGRESS,
            assigned_to="CTO",
            created_at=datetime.datetime.now().isoformat()
        )
        
        self.state.milestones.append(milestone)
        self.state.current_milestone_id = milestone_id
        self.state_manager.save_state(self.state)
        
        try:
            # Process through team
            results = {}
            for role, agent in self.agents.items():
                context = {
                    "project_state": self.state.to_dict(),
                    "current_milestone": asdict(milestone),
                    "previous_results": results
                }
                
                result = await agent.process_message(
                    f"Process milestone: {milestone_description}",
                    context
                )
                
                results[role] = result
                
                # Update milestone feedback
                milestone.feedback.append({
                    "role": role,
                    "feedback": result,
                    "timestamp": datetime.datetime.now().isoformat()
                })
            
            # Update milestone status
            milestone.status = ProjectStatus.COMPLETED
            milestone.completed_at = datetime.datetime.now().isoformat()
            self.state_manager.save_state(self.state)
            
            return results
            
        except Exception as e:
            milestone.status = ProjectStatus.ON_HOLD
            self.state_manager.save_state(self.state)
            raise

async def main():
    # Example usage
    try:
        project_id = "example_project"
        team = SoftwareTeam(project_id)
        
        # Check if project exists
        existing_state = team.state_manager.load_state(project_id)
        
        if not existing_state:
            # Start new project
            requirements = """
            Create a web application that allows users to:
            1. Upload and analyze CSV files
            2. Generate interactive visualizations
            3. Export reports in PDF format
            """
            await team.start_new_project("Data Analysis Web App", requirements)
        else:
            # Resume existing project
            await team.resume_project()
        
        # Process new milestone
        milestone_description = "Implement CSV file upload and validation feature"
        results = await team.process_milestone(milestone_description)
        
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
