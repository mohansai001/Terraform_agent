from tf_agent import terraform_agent
from vida.models.requests.Agents_requests import terraform_agent_request
from fastapi import APIRouter

router = APIRouter()

@router.post("/terraform-agent")
async def terraform_agent_call(request: terraform_agent_request):
    agent=terraform_agent()
    session=request.session
    response = await agent.run(
        prompt=request.prompt,
        session=session
    )
    print(vars(session))
    print(agent._session.session_id)
    return {"response": response}