import json
import os
import requests
from playwright.sync_api import sync_playwright

FACEBOOK_URL = "https://www.facebook.com/Shinedown/"
STATE_FILE = "state.json"

WEBHOOK = os.environ["DISCORD_WEBHOOK"]


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"posts": []}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"posts": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def send_discord(post_url, text, image_url=None):
    embed = {
        "title": "Shinedown — New Facebook Post",
        "url": post_url,
        "description": text[:4000],
        "footer": {
            "text": "Shinedown on Facebook"
        }
    }

    if image_url:
        embed["image"] = {"url": image_url}

    response = requests.post(
        WEBHOOK,
        json={"embeds": [embed]},
        timeout=30
    )

    response.raise_for_status()


def main():
    state = load_state()
    known_posts = set(state.get("posts", []))
    posts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = browser.new_page(
            viewport={"width": 1280, "height": 2000},
            locale="en-US"
        )

        print("Opening Shinedown Facebook page...")

        page.goto(
            FACEBOOK_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(8000)

        for _ in range(3):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(2500)

        links = page.locator("a").all()

        for link in links:
            try:
                href = link.get_attribute("href")

                if not href:
                    continue

                if "/posts/" not in href and "/photos/" not in href:
                    continue

                if href.startswith("/"):
                    href = "https://www.facebook.com" + href

                href = href.split("?")[0]

                if href not in [p["url"] for p in posts]:
                    posts.append({
                        "url": href,
                        "text": "",
                        "image": None
                    })

            except Exception:
                continue

        browser.close()

    print(f"Found {len(posts)} possible posts.")

    new_posts = [
        post for post in posts
        if post["url"] not in known_posts
    ]

    new_posts = new_posts[:3]

    for post in reversed(new_posts):
        print("Sending:", post["url"])

        try:
            send_discord(
                post["url"],
                "New Shinedown post on Facebook.\n\n"
                "Click the title to view the post."
            )

            known_posts.add(post["url"])

        except Exception as e:
            print("Discord error:", e)

    state["posts"] = list(known_posts)[-100:]
    save_state(state)


if __name__ == "__main__":
    main()
