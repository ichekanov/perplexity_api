from fastapi import APIRouter, HTTPException
from starlette import status

from app.schemas import PerplexityRequest, PerplexityResponse, PerplexityStatus, PerplexityUnavailableResponse
from app.utils import Perplexity


api_router = APIRouter(tags=["Perplexity"], prefix="/perplexity")
perplexity_client = Perplexity()


@api_router.post(
    "/ask",
    response_model=PerplexityResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Request cannot be processed at the moment, try again later",
            "model": PerplexityUnavailableResponse,
        },
    },
)
async def ask_perplexity(request: PerplexityRequest):
    if perplexity_client.status != PerplexityStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PerplexityUnavailableResponse(status=perplexity_client.status, message=perplexity_client.status),
        )
    response = await perplexity_client.ask(query=request.message, mode=request.mode)
    return PerplexityResponse(message=response)
