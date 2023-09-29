from os import environ

from pydantic_settings import BaseSettings, SettingsConfigDict


class DefaultSettings(BaseSettings):
    """
    Default configs for application.

    Usually, we have three environments: for development, testing and production.
    But in this situation, we only have standard settings for local development.
    """

    # Application settings
    ENV: str = environ.get("ENV", "local")
    PATH_PREFIX: str = environ.get("PATH_PREFIX", "/api")
    APP_HOST: str = environ.get("APP_HOST", "http://127.0.0.1")
    APP_PORT: int = int(environ.get("APP_PORT", 8000))

    CAPMONSTER_API_KEY: str = environ.get("CAPMONSTER_API_KEY", "")

    PERPLEXITY_CLOUDFLARE_KEY: str = environ.get("PERPLEXITY_CLOUDFLARE_KEY", "")
    PERPLEXITY_URL: str = environ.get("PERPLEXITY_URL", "https://www.perplexity.ai/")
    PERPLEXITY_UPDATE_INTERVAL: int = int(environ.get("PERPLEXITY_UPDATE_INTERVAL", 60 * 60 * 1))

    PROXY_HOST: str = environ.get("PROXY_HOST", "")
    PROXY_LOGIN: str = environ.get("PROXY_LOGIN", "")
    PROXY_PASSWORD: str = environ.get("PROXY_PASSWORD", "")
    PROXY_PORT: int = int(environ.get("PROXY_PORT", 3128))

    @property
    def app_path(self) -> str:
        """
        Get uri for connection with app.
        """
        return f"{self.APP_HOST}:{self.APP_PORT}{self.PATH_PREFIX}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
