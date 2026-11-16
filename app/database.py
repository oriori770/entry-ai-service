import logging
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings

logger = logging.getLogger("entry_ai")

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None
_is_connected: bool = False

# Collections in the existing MongoDB schema
COLLECTION_ENTRIES = "entries"
COLLECTION_EVENTS = "events"
COLLECTION_PARTICIPANTS = "participants"
COLLECTION_USERS = "users"

ALLOWED_COLLECTIONS = {
    COLLECTION_ENTRIES,
    COLLECTION_EVENTS,
    COLLECTION_PARTICIPANTS,
    COLLECTION_USERS,
}

FORBIDDEN_PIPELINE_STAGES = {"$out", "$merge"}


async def connect_db() -> None:
    """Initializes the MongoDB connection with a ping check."""
    global _client, _db, _is_connected
    settings = get_settings()

    try:
        logger.info(f"Connecting to MongoDB at [cyan]{settings.mongodb_uri}[/cyan]...")
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=2500,
            connectTimeoutMS=2500,
        )
        _db = _client[settings.mongodb_db_name]

        # Verify connection with ping
        await _client.admin.command("ping")
        _is_connected = True
        logger.info("[bold green]MongoDB connected successfully (Read-Only accessors active).[/bold green]")
    except Exception as exc:
        _is_connected = False
        logger.warning(
            f"[bold yellow]MongoDB connection warning:[/bold yellow] Could not reach MongoDB ({exc}). "
            "Server running in offline/graceful mode."
        )


async def disconnect_db() -> None:
    """Closes the MongoDB connection."""
    global _client, _db, _is_connected
    if _client:
        _client.close()
        _client = None
        _db = None
        _is_connected = False
        logger.info("[yellow]MongoDB connection closed.[/yellow]")


def is_db_connected() -> bool:
    """Returns whether MongoDB is currently reachable."""
    return _is_connected


def _get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database is not initialized or unreachable.")
    return _db


def _sanitize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Converts MongoDB BSON types (like ObjectId) to JSON-serializable strings."""
    sanitized = {}
    for key, value in doc.items():
        if key == "_id":
            sanitized["_id"] = str(value)
        elif hasattr(value, "isoformat"):
            sanitized[key] = value.isoformat()
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_doc(value)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_doc(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


# =========================================================================
# Read-Only Query Accessors Layer (Zero mutable methods exposed)
# =========================================================================

async def run_readonly_aggregate(
    collection_name: str,
    pipeline: List[Dict[str, Any]],
    max_results: int = 100,
) -> List[Dict[str, Any]]:
    """
    Executes a read-only aggregation pipeline.
    Rejects any stages attempting to modify or write data ($out, $merge).
    """
    if collection_name not in ALLOWED_COLLECTIONS:
        raise ValueError(f"Collection '{collection_name}' is not in allowed read-only collections.")

    # Guard against write stages
    for stage in pipeline:
        for key in stage.keys():
            if key in FORBIDDEN_PIPELINE_STAGES:
                raise ValueError(f"Forbidden pipeline stage '{key}' detected in read-only query.")

    # Ensure result limits
    safe_pipeline = list(pipeline)
    has_limit = any("$limit" in stage for stage in safe_pipeline)
    if not has_limit:
        safe_pipeline.append({"$limit": max_results})

    db = _get_db()
    cursor = db[collection_name].aggregate(safe_pipeline)
    results = await cursor.to_list(length=max_results)
    return [_sanitize_doc(doc) for doc in results]


async def find_participant_by_barcode(barcode: str) -> Optional[Dict[str, Any]]:
    """Fetches participant details by their unique barcode string."""
    clean_barcode = barcode.strip()
    db = _get_db()
    doc = await db[COLLECTION_PARTICIPANTS].find_one({"barcode": clean_barcode})
    return _sanitize_doc(doc) if doc else None


async def find_entries_for_barcode(barcode: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches scan history entries for a given barcode, newest first."""
    clean_barcode = barcode.strip()
    db = _get_db()
    cursor = db[COLLECTION_ENTRIES].find({"barcode": clean_barcode}).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_sanitize_doc(doc) for doc in docs]


async def find_events(filter_query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Fetches all events or filtered events."""
    query = filter_query or {}
    db = _get_db()
    cursor = db[COLLECTION_EVENTS].find(query).sort("createdAt", -1).limit(100)
    docs = await cursor.to_list(length=100)
    return [_sanitize_doc(doc) for doc in docs]
