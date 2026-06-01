from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import Role, User
from app.schemas.graph import ConversationGraph
from app.schemas.packet import PacketSummary
from app.services.capture import get_artifact
from app.services.packet_query import (
    build_conversation_graph,
    get_conversation_packets,
)

router = APIRouter(prefix="/api/captures/{artifact_id}", tags=["graph"])


async def _resolve_artifact(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
) -> tuple[int, str]:
    """Resolve artifact_id to (artifact_id, file_path), or 404."""
    artifact = await get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture artifact not found",
        )
    return artifact_id, artifact.file_path


@router.get("/graph", response_model=ConversationGraph)
async def get_conversation_graph(
    artifact_id: int,
    resolved: tuple[int, str] = Depends(_resolve_artifact),
):
    """Get the Conversation Graph (nodes + edges) for a capture artifact."""
    aid, file_path = resolved
    graph = build_conversation_graph(file_path)
    return ConversationGraph(
        nodes=[{"id": n.id, "ip_address": n.ip_address, "label": n.label} for n in graph.nodes],
        edges=[
            {
                "id": e.id,
                "source_node": e.source_node,
                "target_node": e.target_node,
                "protocol": e.protocol,
                "packet_count": e.packet_count,
                "byte_count": e.byte_count,
                "error_count": e.error_count,
                "conversation_id": e.conversation_id,
            }
            for e in graph.edges
        ],
        artifact_id=aid,
    )


@router.get("/graph/edges/{edge_id}/packets", response_model=list[PacketSummary])
async def get_edge_packets(
    artifact_id: int,
    edge_id: int,
    resolved: tuple[int, str] = Depends(_resolve_artifact),
):
    """Get the packet subset for a graph edge (maps edge_id to conversation)."""
    _, file_path = resolved
    packets = get_conversation_packets(file_path, edge_id)
    if packets is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph edge {edge_id} not found",
        )
    return packets
