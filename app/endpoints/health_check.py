from datetime import timedelta

from fastapi import APIRouter
from starlette import status

from app.config import get_settings
from app.schemas import PerplexityStatusResponse, PingResponse
from app.utils import Perplexity


api_router = APIRouter(tags=["Status"], prefix="/status")
perplexity_client = Perplexity()


@api_router.get(
    "/ping",
    response_model=PingResponse,
    status_code=status.HTTP_200_OK,
)
async def health_check():
    return PingResponse()


@api_router.get(
    "/perplexity",
    response_model=PerplexityStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def perplexity_check():
    return PerplexityStatusResponse(
        status=perplexity_client.status,
        message=perplexity_client.status,
        copilots_left=perplexity_client.copilots_left,
        last_authenticated=perplexity_client.last_update,
        next_authentication=perplexity_client.last_update
        + timedelta(seconds=get_settings().PERPLEXITY_UPDATE_INTERVAL),
    )
