import os
from playwright.sync_api import sync_playwright

FACEBOOK_URL = "https://www.facebook.com/Shinedown/"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
    )

    page = browser.new_page(
        viewport={
            "width": 1280,
            "height": 2000
        },
        locale="en-US",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    )

    print("Opening Shinedown Facebook page...")

    try:
        response = page.goto(
            FACEBOOK_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("HTTP status:", response.status if response else "unknown")
        print("Final URL:", page.url)
        print("Page title:", page.title())

        page.wait_for_timeout(10000)

        text = page.locator("body").inner_text()

        print("Page text length:", len(text))
        print("First 5000 characters:")
        print(text[:5000])

        os.makedirs("debug", exist_ok=True)

        with open(
            "debug/facebook.html",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(page.content())

        page.screenshot(
            path="debug/facebook.png",
            full_page=True
        )

        print("Saved debug files.")

    except Exception as error:
        print("ERROR:", error)

    browser.close()
