from tf_agent import TfAgent
from vida.models.requests.Agents_requests import terraform_agent_request
from fastapi import APIRouter
from vida.utils.preprocess import try_parse_json
from vida.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/terraform-agent")
async def terraform_agent_call(request: terraform_agent_request):
    agent=TfAgent.get_instance()
    session=request.session
    response = await agent.run(
        prompt=request.prompt,
        session=session
    )
    logger.info("[terraform_agent] Successfully generated Terraform agent instance.")
    print("[terraform_agent] Successfully generated Terraform agent instance.")
    output, is_json = try_parse_json(response.text)
    return {
        "response": f"Terraform agent executed successfully",
        "raw": response,
        "is_json": is_json,
        "output": output
    }
    # print(agent._session.session_id)
    # return {"response": response}