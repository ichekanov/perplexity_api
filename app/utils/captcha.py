import asyncio
import base64

import httpx
from selenium.webdriver.common.by import By
from seleniumwire import webdriver

from app.config import get_settings


class CaptchaError(Exception):
    pass


async def check_capmonster_balance(web_session: httpx.AsyncClient) -> float:
    resp = await web_session.post(
        "https://api.capmonster.cloud/getBalance", json={"clientKey": get_settings().CAPMONSTER_API_KEY}
    )
    data = resp.json()
    return data["balance"]


async def request_cloudfare_challenge(web_session: httpx.AsyncClient, user_agent: str, page_source_b64: str) -> int:
    settings = get_settings()
    resp = await web_session.post(
        "https://api.capmonster.cloud/createTask",
        json={
            "clientKey": settings.CAPMONSTER_API_KEY,
            "task": {
                "type": "TurnstileTask",
                "cloudflareTaskType": "cf_clearance",
                "websiteURL": settings.PERPLEXITY_URL,
                "websiteKey": settings.PERPLEXITY_CLOUDFLARE_KEY,  # method could be found in selenium.ipynb
                "proxyType": "http",
                "proxyAddress": settings.APP_HOST,  # https://anti-captcha.com/ru/apidoc/articles/how-to-install-squid
                "proxyPort": settings.PROXY_PORT,
                "proxyLogin": settings.PROXY_LOGIN,
                "proxyPassword": settings.PROXY_PASSWORD,
                "htmlPageBase64": page_source_b64,
                "userAgent": user_agent,
            },
        },
    )
    data = resp.json()
    return data["taskId"]


async def get_cloudfare_challenge_result(web_session: httpx.AsyncClient, task_id: int) -> str:
    settings = get_settings()
    counter = 30
    data = None
    while counter > 0:
        await asyncio.sleep(5)
        resp = await web_session.post(
            "https://api.capmonster.cloud/getTaskResult",
            json={
                "clientKey": settings.CAPMONSTER_API_KEY,
                "taskId": task_id,
            },
        )
        data = resp.json()
        if "status" in data and data["status"] == "ready":
            return data["solution"]["cf_clearance"]
        if "status" not in data:
            raise CaptchaError(f"Captcha was not solved: {data}")
        counter -= 1
    raise CaptchaError(f"Captcha was not solved (timeout): {data}")


def get_cookies_dict(driver: webdriver.Chrome) -> dict[str, str]:
    cookies = {}
    for request in driver.get_cookies():
        cookies[request["name"]] = request["value"]
    return cookies


def get_perplexity_cookies(driver: webdriver.Chrome) -> dict[str, str]:
    cookies = {}
    for request in driver.requests:
        if "api/auth/signin/email" in request.url:
            for cookie in request.headers.get("cookie").split(";"):
                name, value = cookie.split("=", 1)
                cookies[name.strip()] = value.strip()
            return cookies
    raise FileNotFoundError("Perplexity cookies not found")


def get_perplexity_headers(driver: webdriver.Chrome) -> dict[str, str]:
    browser_headers = {}
    for request in driver.requests:
        browser_headers.update(request.headers)
    perplexity_headers = {
        "authority": "www.perplexity.ai",
        "accept": "*/*",
        "accept-language": "ru",
        "baggage": browser_headers["baggage"],
        "content-type": "application/x-www-form-urlencoded",
        "dnt": "1",
        "origin": "https://www.perplexity.ai",
        "referer": "https://www.perplexity.ai/",
        "sec-ch-ua": browser_headers["sec-ch-ua"],
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": browser_headers["sec-ch-ua-platform"],
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sentry-trace": browser_headers["sentry-trace"],
        "user-agent": browser_headers["user-agent"],
    }
    return perplexity_headers


def get_emailnator_auth_data(driver: webdriver.Chrome) -> tuple[dict[str, str], dict[str, str]]:
    message_request = None
    for request in driver.requests:
        if "message-list" in request.url:
            message_request = request
            break
    if not message_request:
        raise CaptchaError("'https://www.emailnator.com/message-list' request not found")
    emailnator_headers = {
        "authority": "www.emailnator.com",
        "accept": "application/json, text/plain, */*",
        "accept-language": "ru",
        "content-type": "application/json",
        "dnt": "1",
        "origin": "https://www.emailnator.com",
        "referer": "https://www.emailnator.com/inbox",
        "sec-ch-ua": '"Not)A;Brand";v="24", "Chromium";v="116"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": message_request.headers.get("user-agent"),
        "x-requested-with": "XMLHttpRequest",
        "x-xsrf-token": message_request.headers.get("x-xsrf-token"),
    }
    emailnator_cookies = {}
    for cookie in message_request.headers.get("cookie").split(";"):
        name, value = cookie.split("=", 1)
        emailnator_cookies[name.strip()] = value.strip()
    return emailnator_headers, emailnator_cookies


async def auth_perplexity(browser: webdriver.Chrome) -> tuple[dict[str, str], dict[str, str]]:
    settings = get_settings()
    loop = asyncio.get_event_loop()
    user_agent = browser.execute_script("return navigator.userAgent;")
    browser.get(settings.PERPLEXITY_URL)
    # await loop.run_in_executor(None, browser.get, settings.PERPLEXITY_URL)
    page_source_b64 = base64.b64encode(browser.page_source.encode("utf-8")).decode("utf-8")
    async with httpx.AsyncClient() as web_session:
        if await check_capmonster_balance(web_session) < 0.002:
            raise CaptchaError("Not enough money on capmonster balance")
        task_id = await request_cloudfare_challenge(web_session, user_agent, page_source_b64)
        cf_clearance = await get_cloudfare_challenge_result(web_session, task_id)
    browser.add_cookie({"name": "cf_clearance", "value": cf_clearance})
    browser.get(settings.PERPLEXITY_URL)
    print(f"{browser.title=}")
    # await loop.run_in_executor(None, browser.get, settings.PERPLEXITY_URL)
    browser.find_element(By.XPATH, "//div[normalize-space()='Sign Up']").click()
    await asyncio.sleep(1)
    browser.find_element(By.XPATH, "//input[@type='email']").send_keys("aa@aa.aa")
    await asyncio.sleep(1)
    browser.find_element(By.XPATH, "//div[contains(text(), 'Continue with Email')]").click()
    await asyncio.sleep(1)
    cookies = get_perplexity_cookies(browser)
    headers = get_perplexity_headers(browser)
    return headers, cookies


async def auth_emailnator(browser: webdriver.Chrome) -> tuple[dict[str, str], dict[str, str]]:
    loop = asyncio.get_event_loop()
    # browser.get("https://www.emailnator.com/")
    await loop.run_in_executor(None, browser.get, "https://www.emailnator.com/")
    browser.find_element(By.NAME, "goBtn").click()
    await asyncio.sleep(3)
    headers, cookies = get_emailnator_auth_data(browser)
    return headers, cookies
