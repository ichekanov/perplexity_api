from pydantic import BaseModel, Field, field_serializer, field_validator

from .custom import PerplexityMode, PerplexityStatus


class PerplexityRequest(BaseModel):
    mode: PerplexityMode = Field(default=PerplexityMode.COPILOT, description="Perplexity mode to use.")
    message: str = Field(default="What is the meaning of life?", description="Question to perplexity.")


class PerplexityResponse(BaseModel):
    message: dict = Field(default={"response": "This is the answer"}, description="Response from perplexity.")


class PerplexityUnavailableResponse(BaseModel):
    status: PerplexityStatus = Field(
        default=PerplexityStatus.INIT, examples=[PerplexityStatus.INIT.name], description="Perplexity status."
    )
    message: str = Field(
        default="Perplexity is unavailable at the moment, try again later.", description="Human-readable status."
    )

    @field_serializer("status")
    def serialize_status(self, v):
        return v.name
