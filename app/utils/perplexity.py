from datetime import datetime, timedelta
from logging import getLogger

from pyvirtualdisplay import Display
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver

from .captcha import auth_emailnator, auth_perplexity
from .perplexity_client import Client as PerplexityClient
from app.config import get_settings
from app.schemas import PerplexityMode, PerplexityStatus


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
    class AuthData:
        def __init__(self, headers: dict[str, str], cookies: dict[str, str]):
            self.headers = headers
            self.cookies = cookies

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
        self.copilots_left: int = 0
        self._perplexity_auth: Perplexity.AuthData | None = None
        self._emailnator_auth: Perplexity.AuthData | None = None
        self.last_update: datetime = datetime.fromtimestamp(0)

    async def _renew_cookies(self):
        self.status = PerplexityStatus.UPDATING
        self.last_update = datetime.now()
        with Browser(self._chrome_options, force_timeout=5) as browser:
            self._perplexity_auth = Perplexity.AuthData(*await auth_perplexity(browser))
            self._logger.info("[PERPLEXITY] Perplexity headers: %s", self._perplexity_auth.headers)
            self._logger.info("[PERPLEXITY] Perplexity cookies: %s", self._perplexity_auth.cookies)
            self._emailnator_auth = Perplexity.AuthData(*await auth_emailnator(browser))
            self._logger.info("[PERPLEXITY] Emailnator headers: %s", self._emailnator_auth.headers)
            self._logger.info("[PERPLEXITY] Emailnator cookies: %s", self._emailnator_auth.cookies)
        self.copilots_left = 5
        self.status = PerplexityStatus.READY

    async def _create_client(self) -> PerplexityClient:
        if (
            self.copilots_left == 0
            or self._perplexity_auth is None
            or self.last_update + timedelta(seconds=get_settings().PERPLEXITY_UPDATE_INTERVAL) < datetime.now()
        ):
            self._logger.info("[PERPLEXITY] Fetching credentials for new client...")
            await self._renew_cookies()
            self._logger.info("[PERPLEXITY] Credentials fetched. Authenticating...")
        else:
            self._logger.info("[PERPLEXITY] Using existing credentials for new client. Authenticating...")
        client = await PerplexityClient(self._perplexity_auth.headers, self._perplexity_auth.cookies)
        self._logger.info("[PERPLEXITY] Authenticated. Creating account...")
        await client.create_account(self._emailnator_auth.headers, self._emailnator_auth.cookies)
        self._logger.info("[PERPLEXITY] Account created.")
        return client

    async def ask(self, query: str, mode: PerplexityMode) -> str:
        self.status = PerplexityStatus.BUSY
        if mode == PerplexityMode.COPILOT:
            self.copilots_left -= 1
        client = await self._create_client()
        response = await client.search(query=query, mode=mode)
        await client.session.close()
        client.ws.close()
        del client
        self.status = PerplexityStatus.READY
        return response
