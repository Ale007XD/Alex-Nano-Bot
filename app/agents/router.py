"""
Agent router - routes messages to appropriate agent
"""
from typing import Dict, Optional, Any
from enum import Enum

from app.agents.nanobot import nanobot
from app.agents.claudbot import claudbot
from app.agents.moltbot import moltbot
from app.core.database import UserState
import logging

logger = logging.getLogger(__name__)


class AgentMode(Enum):
    """Available agent modes"""
    NANOBOT = "nanobot"
    CLAUDBOT = "claudbot"
    MOLTBOT = "moltbot"


class AgentRouter:
    """Routes messages to appropriate agent based on mode and context"""
    
    def __init__(self):
        self.agents = {
            AgentMode.NANOBOT.value: nanobot,
            AgentMode.CLAUDBOT.value: claudbot,
            AgentMode.MOLTBOT.value: moltbot,
        }
        self.default_agent = AgentMode.NANOBOT.value
    
    async def route_message(
        self,
        user_id: int,
        message: str,
        agent_mode: Optional[str] = None,
        conversation_history: Optional[list] = None
    ) -> str:
        """
        Route message to appropriate agent
        
        Args:
            user_id: User's Telegram ID
            message: User's message
            agent_mode: Force specific agent mode (optional)
            conversation_history: Previous messages
            
        Returns:
            Agent's response
        """
        # Determine agent to use
        mode = agent_mode or self.default_agent
        
        # Get agent instance
        agent = self.agents.get(mode, self.agents[self.default_agent])
        
        logger.info(f"Routing message to {agent.name} for user {user_id}")
        
        # Process through agent
        try:
            response = await agent.process_message(
                user_id=user_id,
                message=message,
                conversation_history=conversation_history
            )
            return response
        except Exception as e:
            logger.error(f"Agent {agent.name} failed: {e}")
            return f"⚠️ Sorry, I'm having trouble processing your request. Please try again."
    
    def get_agent(self, mode: str) -> Optional[Any]:
        """Get agent by mode"""
        return self.agents.get(mode)
    
    def list_agents(self) -> Dict[str, Any]:
        """List all available agents"""
        return self.agents.copy()
    
    def get_agent_info(self, mode: str) -> Optional[Dict[str, str]]:
        """Get agent information"""
        agent = self.agents.get(mode)
        if agent:
            return {
                "name": agent.name,
                "display_name": agent.display_name,
                "description": agent.description
            }
        return None


# Global router instance
agent_router = AgentRouter()
