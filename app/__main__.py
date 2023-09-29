from logging import getLogger

from fastapi import FastAPI
from uvicorn import run

from app.config import DefaultSettings
from app.config.utils import get_settings
from app.endpoints import list_of_routes
from app.utils import Perplexity, get_hostname


def bind_routes(application: FastAPI, setting: DefaultSettings) -> None:
    """
    Binds all routes to application.
    """
    for route in list_of_routes:
        application.include_router(route, prefix=setting.PATH_PREFIX)


def get_app() -> FastAPI:
    """
    Creates application and all dependable objects.
    """
    application = FastAPI(
        title="Perplexity *pirate* API",
        description="Unofficial API for Perplexity AI service.",
        docs_url="/swagger",
        openapi_url="/openapi",
        version="1.0.0",
    )

    settings = get_settings()
    bind_routes(application, settings)
    application.state.settings = settings

    return application


app = get_app()


@app.on_event("startup")
async def startup_event() -> None:
    """
    Runs on application startup.
    """
    logger = getLogger("uvicorn.info")
    logger.info("Starting Perplexity module...")
    client = Perplexity()
    await client.update_client()


if __name__ == "__main__":  # pragma: no cover
    settings_for_application = get_settings()
    run(
        "app.__main__:app",
        host=get_hostname(settings_for_application.APP_HOST),
        port=settings_for_application.APP_PORT,
        # reload=True,
        reload_dirs=["app", "tests"],
        log_level="debug",
    )
