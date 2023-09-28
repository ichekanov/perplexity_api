from fastapi import APIRouter
from starlette import status

from app.schemas import PerplexityStatusResponse, PingResponse


api_router = APIRouter(tags=["Status"], prefix="/status")


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
    # todo: implement perplexity check
    return PerplexityStatusResponse()
