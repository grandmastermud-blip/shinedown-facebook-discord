import json
import os
import requests
from datetime import datetime, timezone
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

        if not line:
            continue

        if line not in lines:
            lines.append(line)

    return "\n".join(lines)


def get_image(article):
    images = article.locator("img").all()

    for image in images:
        try:
            src = image.get_attribute("src")

            if src and src.startswith("http"):
                return src

        except Exception:
            continue

    return None


def get_post_id(article):
    links = article.locator("a").all()

    for link in links:
        try:
            href = link.get_attribute("href")

            if not href:
                continue

            if "/posts/" in href:
                return href.split("?")[0]

            if "/photos/" in href:
                return href.split("?")[0]

            if "/videos/" in href:
                return href.split("?")[0]

        except Exception:
            continue

    text = article.inner_text()

    return "text:" + str(hash(text))


def extract_posts(page):
    posts = []

    articles = page.locator("div[role='article']").all()

    print(f"Found {len(articles)} article elements.")

    for article in articles:
        try:
            text = clean_text(article.inner_text())

            if len(text) < 30:
                continue

            if "Shinedown" not in text:
                continue

            post_id = get_post_id(article)

            image = get_image(article)

            posts.append({
                "id": post_id,
                "text": text,
                "image": image,
                "date": datetime.now(timezone.utc).isoformat()
            })

        except Exception as error:
            print("Article error:", error)

    return posts


def send_discord(post):
    text = post["text"]

    if len(text) > 4000:
        text = text[:3997] + "..."

    embed = {
        "author": {
            "name": "Shinedown",
            "url": FACEBOOK_URL
        },
        "title": "New Facebook Post",
        "description": text,
        "url": post["id"],
        "footer": {
            "text": "Shinedown on Facebook"
        },
        "timestamp": post["date"]
    }

    if post["image"]:
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


def main():
    state = load_state()

    known_posts = set(state.get("posts", []))

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
                page.wait_for_timeout(2500)

            posts = extract_posts(page)

        except Exception as error:
            print("Facebook error:", error)
            posts = []

        browser.close()

    print(f"Found {len(posts)} possible posts.")

    new_posts = []

    for post in posts:
        if post["id"] not in known_posts:
            new_posts.append(post)

    print(f"Found {len(new_posts)} new posts.")

    new_posts = new_posts[:3]

    for post in reversed(new_posts):
        print("Sending:", post["id"])

        try:
            send_discord(post)

            known_posts.add(post["id"])

            print("Sent successfully.")

        except Exception as error:
            print("Discord error:", error)

    state["posts"] = list(known_posts)[-100:]

    save_state(state)


if __name__ == "__main__":
    main()
