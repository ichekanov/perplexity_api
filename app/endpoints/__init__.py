from .health_check import api_router as health_check_router
from .perplexity import api_router as perplexity_router


list_of_routes = [
    health_check_router,
    perplexity_router,
]


__all__ = [
    "list_of_routes",
]
