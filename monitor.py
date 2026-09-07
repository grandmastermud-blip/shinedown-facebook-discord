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

    page.goto(
        FACEBOOK_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(10000)

    body_text = page.locator("body").inner_text()

    print("Page text length:", len(body_text))

    if "Young Again" in body_text:
        print("Found Young Again in page text.")

        locator = page.get_by_text("Young Again", exact=False)

        print("Young Again matches:", locator.count())

        if locator.count() > 0:
            element = locator.first

            print("Element tag:", element.evaluate("(e) => e.tagName"))
            print("Element text:", element.inner_text())

            html = element.evaluate(
                "(e) => e.parentElement.parentElement.outerHTML"
            )

            print("HTML around Young Again:")
            print(html[:15000])

    else:
        print("Young Again was NOT found.")

    print("All links containing posts/photos/videos:")

    links = page.locator("a").all()

    count = 0

    for link in links:
        try:
            href = link.get_attribute("href")

            if href and any(
                x in href
                for x in ["/posts/", "/photos/", "/videos/", "/reel/"]
            ):
                print(href)
                count += 1

        except Exception:
            pass

    print("Matching links:", count)

    browser.close()
