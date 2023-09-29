import asyncio
import concurrent.futures
from datetime import datetime
from logging import getLogger

from pyvirtualdisplay import Display
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver

from .captcha import auth_emailnator, auth_perplexity
from .common import AsyncMixin
from .perplexity_client import Client as PerplexityClient
from app.config import get_settings
from app.schemas import PerplexityStatus


class Browser:
    def __init__(
        self, chrome_options: Options, force_timeout: int | None = None, display_size: tuple[int, int] = (1000, 1000)
    ):
        settings = get_settings()
        if settings.ENV != "local":
            self.display = Display(visible=False, size=display_size)
        else:
            self.display = None
        self.chrome_options = chrome_options
        self.seleniumwire_options = None
        if settings.PROXY_HOST and settings.ENV == "local":
            address = f"{settings.PROXY_HOST}:{settings.PROXY_PORT}"
            if settings.PROXY_LOGIN and settings.PROXY_PASSWORD:
                address = f"{settings.PROXY_LOGIN}:{settings.PROXY_PASSWORD}@{address}"
            elif settings.PROXY_LOGIN:
                address = f"{settings.PROXY_LOGIN}@{address}"
            address = f"http://{address}"
            self.seleniumwire_options = {"proxy": {"http": address}}
        self.driver = None
        self.force_timeout = force_timeout

    def __enter__(self) -> webdriver.Chrome:
        if self.display:
            self.display.start()
        self.driver = webdriver.Chrome(seleniumwire_options=self.seleniumwire_options, options=self.chrome_options)
        if self.force_timeout:
            stop_script = (
                """
                var counter = 0;
                var interval = setInterval(function() {
                    counter++;
                    if (counter === %d) {
                        clearInterval(interval); // stop the interval
                        window.stop(); // this will abort loading
                    }
                }, 1000);
            """
                % self.force_timeout
            )
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": stop_script})
        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        if self.driver:
            self.driver.quit()
            self.driver = None
        if self.display:
            self.display.stop()


class Perplexity:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super(Perplexity, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self._logger = getLogger("uvicorn.debug")
        self.status: PerplexityStatus = PerplexityStatus.INIT
        self._chrome_options = Options()
        self._chrome_options.add_argument("--no-sandbox")
        self._chrome_options.add_argument("--disable-gpu")
        self._chrome_options.add_argument("--disable-dev-shm-usage")
        self._chrome_options.add_argument("--start-maximized")
        self._client: PerplexityClient | None = None
        self.last_update: datetime = datetime.now()

    async def _create_client(self) -> PerplexityClient:
        self._logger.info("[PERPLEXITY] Fetching credentials for new client...")
        with Browser(self._chrome_options, force_timeout=5) as browser:
            perplexity_headers, perplexity_cookies = await auth_perplexity(browser)
            self._logger.info("[PERPLEXITY] Perplexity headers: %s", perplexity_headers)
            self._logger.info("[PERPLEXITY] Perplexity cookies: %s", perplexity_cookies)
            emailnator_headers, emailnator_cookies = await auth_emailnator(browser)
            self._logger.info("[PERPLEXITY] Emailnator headers: %s", emailnator_headers)
            self._logger.info("[PERPLEXITY] Emailnator cookies: %s", emailnator_cookies)
        self._logger.info("[PERPLEXITY] Credentials fetched. Authenticating...")
        client = await PerplexityClient(perplexity_headers, perplexity_cookies)
        self._logger.info("[PERPLEXITY] Authenticated. Creating account...")
        await client.create_account(emailnator_headers, emailnator_cookies)
        self._logger.info("[PERPLEXITY] Account created.")
        return client

    async def update_client(self) -> None:
        self.status = PerplexityStatus.UPDATING
        self.last_update = datetime.now()
        self._client = await self._create_client()
        # loop = asyncio.get_running_loop()
        # with concurrent.futures.ThreadPoolExecutor() as pool:
            # self._client = await loop.run_in_executor(pool, await self._create_client)
        self.status = PerplexityStatus.READY

    async def ask(self, query: str, mode: str) -> str:
        if not self._client:
            raise RuntimeError("Client is not initialized")
        self.status = PerplexityStatus.BUSY
        response = await self._client.search(query=query, mode=mode)
        self.status = PerplexityStatus.READY
        return response
