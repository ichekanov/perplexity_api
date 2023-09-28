from fastapi import APIRouter, HTTPException
from starlette import status

from app.schemas import PerplexityRequest, PerplexityResponse, PerplexityStatus, PerplexityUnavailableResponse
from app.utils import Perplexity


api_router = APIRouter(tags=["Perplexity"], prefix="/perplexity")


@api_router.post(
    "/ask",
    response_model=PerplexityResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Video cannot be processed at the moment, try again later",
            "model": PerplexityUnavailableResponse,
        },
    },
)
async def ask_perplexity(request: PerplexityRequest):
    client = await Perplexity()
    if client.status != PerplexityStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PerplexityUnavailableResponse(status=client.status, message=client.status),
        )
    response = await client.ask(query=request.message, mode=request.mode)
    return PerplexityResponse(message=response)
