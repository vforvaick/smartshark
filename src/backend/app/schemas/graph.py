from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    ip_address: str
    label: str


class GraphEdge(BaseModel):
    id: int
    source_node: str
    target_node: str
    protocol: str
    packet_count: int
    byte_count: int
    error_count: int
    conversation_id: int


class ConversationGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    artifact_id: int
