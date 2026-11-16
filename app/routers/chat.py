from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from app.auth import get_current_user
from app.models.chat import ChatRequest, ChatResponse
from app.models.user import AuthenticatedUser
from app.services.llm import execute_chat, stream_chat

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    summary="Main AI Chat Completion Endpoint (Stateless)",
    status_code=status.HTTP_200_OK,
    response_model=None,
)
async def chat_endpoint(
    request: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Primary chat completion endpoint.
    - If `stream == False` (default): returns complete JSON ChatResponse.
    - If `stream == True`: returns Server-Sent Events (SSE) streaming tokens.
    """
    if request.stream:
        return StreamingResponse(
            stream_chat(user=user, messages=request.messages),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    response: ChatResponse = await execute_chat(user=user, messages=request.messages)
    return response
