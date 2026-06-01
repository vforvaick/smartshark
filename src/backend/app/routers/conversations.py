from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import Role, User
from app.schemas.conversation import (
    ConversationSummary,
    FollowStreamRequest,
    FollowStreamResponse,
    StreamSegment,
)
from app.schemas.packet import PacketSummary
from app.services.capture import get_artifact
from app.services.packet_query import (
    list_conversations,
    get_conversation_packets,
    follow_stream,
)

router = APIRouter(prefix="/api/captures/{artifact_id}", tags=["conversations"])


async def _resolve_artifact(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
) -> str:
    """Resolve artifact_id to its file_path, or 404."""
    artifact = await get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture artifact not found",
        )
    return artifact.file_path


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_capture_conversations(
    artifact_id: int,
    file_path: str = Depends(_resolve_artifact),
):
    """List conversations/flows for a capture artifact."""
    conversations = list_conversations(file_path)
    return conversations


@router.get(
    "/conversations/{conversation_id}/packets",
    response_model=list[PacketSummary],
)
async def get_conversation_packet_list(
    artifact_id: int,
    conversation_id: int,
    file_path: str = Depends(_resolve_artifact),
):
    """Get the packet subset for a specific conversation."""
    packets = get_conversation_packets(file_path, conversation_id)
    if packets is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    return packets


@router.post("/follow-stream", response_model=FollowStreamResponse)
async def follow_capture_stream(
    artifact_id: int,
    body: FollowStreamRequest,
    file_path: str = Depends(_resolve_artifact),
):
    """Follow a stream (TCP/UDP) and return segments with frame references."""
    segments, error = follow_stream(
        file_path, body.stream_index, body.stream_type
    )
    if error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )
    return FollowStreamResponse(
        stream_type=body.stream_type,
        stream_index=body.stream_index,
        segments=[
            StreamSegment(
                direction=s.direction,
                data=s.data,
                frame_numbers=s.frame_numbers,
            )
            for s in segments
        ],
    )
