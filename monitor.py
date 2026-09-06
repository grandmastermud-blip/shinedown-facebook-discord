import json
import os
import requests
from datetime import datetime
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


def clean_text(text):
    if not text:
        return ""

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line and line not in lines:
            lines.append(line)

    return "\n".join(lines).strip()


def send_discord(post):
    description = post["text"]

    if not description:
        description = "Shinedown made a new post on Facebook."

    if len(description) > 4000:
        description = description[:3997] + "..."

    embed = {
        "author": {
            "name": "Shinedown",
            "url": FACEBOOK_URL
        },
        "title": "New Facebook Post",
        "url": post["url"],
        "description": description,
        "footer": {
            "text": "Shinedown on Facebook"
        },
        "timestamp": post["date"]
    }

    if post.get("image"):
        embed["image"] = {
            "url": post["image"]
        }

    payload = {
        "username": "Shinedown Facebook",
        "embeds": [embed]
    }

    response = requests.post(
        WEBHOOK,
        json=payload,
        timeout=30
    )

    response.raise_for_status()


def extract_posts(page):
    posts = []

    elements = page.locator("a").all()

    for element in elements:
        try:
            href = element.get_attribute("href")

            if not href:
                continue

            if "/posts/" not in href and "/photos/" not in href:
                continue

            if href.startswith("/"):
                href = "https://www.facebook.com" + href

            href = href.split("?")[0]

            if any(post["url"] == href for post in posts):
                continue

            container = element.locator(
                "xpath=ancestor::div[@role='article'][1]"
            )

            if container.count() == 0:
                continue

            text = clean_text(container.inner_text())

            image = None

            images = container.locator("img").all()

            for img in images:
                try:
                    src = img.get_attribute("src")

                    if src and src.startswith("http"):
                        width = img.get_attribute("width")
                        height = img.get_attribute("height")

                        if width and height:
                            try:
                                if int(width) >= 200 and int(height) >= 100:
                                    image = src
                                    break
                            except Exception:
                                pass

                        if not image:
                            image = src

                except Exception:
                    continue

            posts.append({
                "url": href,
                "text": text,
                "image": image,
                "date": datetime.utcnow().isoformat() + "Z"
            })

        except Exception:
            continue

    return posts


def main():
    state = load_state()
    known_posts = set(state.get("posts", []))

    posts = []

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
            page.goto(
                FACEBOOK_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(10000)

            for _ in range(4):
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(3000)

            posts = extract_posts(page)

        except Exception as error:
            print("Facebook error:", error)

        browser.close()

    print(f"Found {len(posts)} possible posts.")

    new_posts = [
        post for post in posts
        if post["url"] not in known_posts
    ]

    new_posts = new_posts[:3]

    print(f"Found {len(new_posts)} new posts.")

    for post in reversed(new_posts):
        print("Sending:", post["url"])

        try:
            send_discord(post)
            known_posts.add(post["url"])
            print("Sent successfully.")

        except Exception as error:
            print("Discord error:", error)

    state["posts"] = list(known_posts)[-100:]
    save_state(state)


if __name__ == "__main__":
    main()
