from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from .custom import PerplexityStatus


class PingResponse(BaseModel):
    message: str = Field(default="Pong!", description="A simple ping response.")


class PerplexityStatusResponse(BaseModel):
    status: PerplexityStatus = Field(
        default=PerplexityStatus.READY,
        examples=[PerplexityStatus.READY.name],
        description="Perplexity status response.",
    )
    message: PerplexityStatus = Field(
        default=PerplexityStatus.READY, description="Human-readable Perplexity status response."
    )
    copilots_left: int = Field(default=0, description="Number of copilots left in current session.")
    last_authenticated: datetime = Field(default=datetime.now(), description="Last credentials update.")
    next_authentication: datetime = Field(default=datetime.now(), description="Next credentials update.")

    @field_serializer("status")
    def serialize_status(self, v):
        return v.name
