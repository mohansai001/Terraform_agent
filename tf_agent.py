from dotenv import load_dotenv
load_dotenv()
from vida.utils.logger import get_logger
from tf_tools.base import TF_Module_builder
from agent_framework import tool #type: ignore
from typing import Annotated
from pydantic import Field
from vida.utils.prompt_manager_v2 import AgentInstructionPrompt, AgentDescriptionPrompt
from vida.agents.Base_agent import Base_Agent

logger = get_logger(__name__)

class TfAgent(Base_Agent):
    name = "terraform_agent"
    instructions = str(AgentInstructionPrompt("tf-agent-instructions"))
    tools=[TF_Module_builder]

@tool(name="terraform_agent",
      description=str(AgentDescriptionPrompt("tf-agent-description")),
      approval_mode="never_require")
async def terraform_agent(): # prompt: Annotated[str, Field(description="Full prompt including original request and any previous context")]):
    logger.info("[terraform_agent] Called with prompt.")
    # print("[terraform_agent] Called with prompt.")
    # logger.debug(f"[terraform_agent] Prompt: {prompt}")
    # print(f"[terraform_agent] Prompt: {prompt}")
    try:
        result = await TfAgent.get_instance() #.run(prompt) #type: ignore
        logger.info("[terraform_agent] Successfully generated Terraform agent instance.")
        print("[terraform_agent] Successfully generated Terraform agent instance.")
        # logger.debug(f"[terraform_agent] Output: {result}")
        # print(f"[terraform_agent] Output: {result}")
        return result
    except Exception as e:
        logger.error(f"[terraform_agent] Error occurred: {e}", exc_info=True)
        print(f"[terraform_agent] Error occurred: {e}")
        raise



