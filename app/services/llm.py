import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional
from app.config import get_settings
from app.models.chat import ActionProposal, ChatResponse, Message
from app.models.user import AuthenticatedUser, UserRole
from app.services.prompts import build_system_prompt

logger = logging.getLogger("entry_ai")

MAX_TOOL_HOPS = 3


def is_mock_mode() -> bool:
    """Returns True if running in test environment or without configured Cloud API keys."""
    settings = get_settings()
    if settings.environment == "test":
        return True
    has_gemini = bool(settings.gemini_api_key.strip())
    has_openai = bool(settings.openai_api_key.strip())
    return not (has_gemini or has_openai)


def generate_mock_response(
    user: AuthenticatedUser,
    messages: List[Message],
) -> ChatResponse:
    """Generates an intelligent simulated Hebrew response based on user role and input."""
    last_user_message = next(
        (m.content for m in reversed(messages) if m.role == "user"),
        "",
    )
    last_lower = last_user_message.lower()

    # BOLA Security Check for Scanner
    if user.role == UserRole.SCANNER:
        forbidden_keywords = [
            "כסף", "הכנסה", "הכנסות", "משתמשים", "דוח", "מנהלים", "רווח",
            "finance", "revenue", "users", "admin", "admins", "analytics",
        ]
        if any(keyword in last_lower for keyword in forbidden_keywords):
            return ChatResponse(
                reply="אין לך הרשאה לגשת לנתונים אלו. שאלות ניהוליות וכספיות זמינות למנהלי מערכת בלבד.",
                action_proposals=None,
                tools_executed=None,
            )

        # Barcode inquiry simulation
        if "ברקוד" in last_lower or "סריקה" in last_lower or "נדחה" in last_lower:
            return ChatResponse(
                reply="מבדיקת הברקוד עולה כי הכרטיס נסרק בהצלחה בשער 1 בשעה 20:15. זוהתה כניסה כפולה.",
                tools_executed=["inspect_ticket"],
            )

        return ChatResponse(
            reply="שלום סדרן. אני כאן כדי לסייע בתחקור כרטיסים, בדיקת סיבות לפסילה ושליפת נהלי שערים.",
            tools_executed=None,
        )

    # Admin Persona
    if "צור" in last_lower and "אירוע" in last_lower:
        proposal = ActionProposal(
            type="create_event",
            payload={
                "name": "אירוע חדש שהוצע ע\"י AI",
                "isActive": True,
                "description": "אירוע שנוסח כטיוטה לבקשת המנהל",
            },
            description="טיוטת יצירת אירוע חדש במערכת הממתינה לאישור סופי",
        )
        return ChatResponse(
            reply="הכנתי עבורך טיוטה ליצירת האירוע המבוקש. שים לב כי האירוע עדיין לא נשמר וממתין לאישורך.",
            action_proposals=[proposal],
            tools_executed=["propose_event_creation"],
        )

    return ChatResponse(
        reply=f"שלום {user.username or 'מנהל'}. מערכת ה-AI עומדת לרשותך לשאלות אנליטיות, אגרגציות נתוני כניסה והכנת אירועים.",
        tools_executed=None,
    )


async def execute_chat(
    user: AuthenticatedUser,
    messages: List[Message],
    tools: Optional[List[Dict[str, Any]]] = None,
) -> ChatResponse:
    """Executes a chat completion turn using LiteLLM (or mock fallback)."""
    settings = get_settings()

    if is_mock_mode():
        return generate_mock_response(user, messages)

    try:
        import litellm
    except ImportError:
        logger.warning("litellm is not installed, falling back to mock mode.")
        return generate_mock_response(user, messages)

    # Setup API key in environment
    if settings.gemini_api_key:
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key

    system_prompt = build_system_prompt(user)
    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        formatted_messages.append({"role": msg.role, "content": msg.content})

    model = settings.ai_model
    tools_executed: List[str] = []
    action_proposals: List[ActionProposal] = []

    try:
        # LiteLLM Completion call
        response = await litellm.acompletion(
            model=model,
            messages=formatted_messages,
            tools=tools if tools else None,
            temperature=0.3,
        )

        content = response.choices[0].message.content or ""
        return ChatResponse(
            reply=content,
            action_proposals=action_proposals if action_proposals else None,
            tools_executed=tools_executed if tools_executed else None,
        )
    except Exception as exc:
        logger.error(f"Error calling LLM provider: {exc}")
        return ChatResponse(
            reply=f"חלה שגיאה זמנית בעת הפנייה לשירות ה-AI: {exc}",
            action_proposals=None,
            tools_executed=None,
        )


async def stream_chat(
    user: AuthenticatedUser,
    messages: List[Message],
    tools: Optional[List[Dict[str, Any]]] = None,
) -> AsyncGenerator[str, None]:
    """Generates Server-Sent Events (SSE) streaming data tokens and final completion metadata."""
    if is_mock_mode():
        mock_response = generate_mock_response(user, messages)
        # Stream text words with tiny sleep to simulate live typing
        words = mock_response.reply.split(" ")
        for word in words:
            chunk_data = json.dumps({"chunk": word + " "}, ensure_ascii=False)
            yield f"data: {chunk_data}\n\n"
            await asyncio.sleep(0.02)

        # Final metadata event
        final_payload = {
            "done": True,
            "tools_executed": mock_response.tools_executed,
            "action_proposals": [p.model_dump() for p in (mock_response.action_proposals or [])],
        }
        yield f"data: {json.dumps(final_payload, ensure_ascii=False)}\n\n"
        return

    # Live streaming via LiteLLM
    import litellm
    settings = get_settings()
    system_prompt = build_system_prompt(user)
    formatted_messages = [{"role": "system", "content": system_prompt}] + [
        {"role": m.role, "content": m.content} for m in messages
    ]

    try:
        response = await litellm.acompletion(
            model=settings.ai_model,
            messages=formatted_messages,
            stream=True,
            temperature=0.3,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                chunk_data = json.dumps({"chunk": delta}, ensure_ascii=False)
                yield f"data: {chunk_data}\n\n"

        # Final event
        yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
    except Exception as exc:
        error_data = json.dumps({"error": str(exc)}, ensure_ascii=False)
        yield f"data: {error_data}\n\n"
