from pydantic import BaseModel


class PacketSummary(BaseModel):
    frame_number: int
    timestamp: str
    source: str
    destination: str
    protocol: str
    length: int
    info: str


class LayerField(BaseModel):
    name: str
    value: str


class FrameDetail(BaseModel):
    frame_number: int
    timestamp: str
    protocols: list[str]
    layers: list[LayerField]


class PayloadPreview(BaseModel):
    hex_dump: str
    ascii: str
    length: int


class FilterValidation(BaseModel):
    valid: bool
    error: str | None = None
