import os
import json
import re
import hashlib
import requests
from playwright.sync_api import sync_playwright

FACEBOOK_URL = "https://www.facebook.com/Shinedown/"
STATE_FILE = "state.json"
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"posts": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def clean_url(url):
    if not url:
        return None
    match = re.search(r"(https://www\.facebook\.com/Shinedown/posts/pfbid[^?]+)", url)
    if match:
        return match.group(1)
    return url

def get_post_id(url, text):
    if url:
        match = re.search(r"pfbid[a-zA-Z0-9]+", url)
        if match:
            return match.group(0)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]

def send_to_discord(text, url, image_url=None):
    embed = {
        "title": "New Shinedown Facebook Post",
        "description": text[:4000],
        "url": url,
        "footer": {
            "text": "Shinedown • Facebook"
        }
    }

    if image_url:
        embed["image"] = {
            "url": image_url
        }

    payload = {
        "username": "Shinedown",
        "embeds": [embed]
    }

    response = requests.post(
        DISCORD_WEBHOOK,
        json=payload,
        timeout=30
    )

    print("Discord response:", response.status_code)

    if response.status_code >= 300:
        print(response.text)

    return response.status_code < 300

def extract_posts(page):
    posts = []

    links = page.locator("a[href*='/Shinedown/posts/pfbid']")
    count = links.count()

    print("Post links found:", count)

    seen = set()

    for i in range(count):
        try:
            link = links.nth(i)
            href = link.get_attribute("href")

            if not href:
                continue

            url = clean_url(href)

            if not url or url in seen:
                continue

            seen.add(url)

            best_container = None
            best_text = ""

            container = link

            for level in range(1, 15):
                try:
                    container = container.locator("..")
                    text = container.inner_text(timeout=2000).strip()

                    if 100 < len(text) < 10000:
                        if len(text) > len(best_text):
                            best_text = text
                            best_container = container

                except:
                    break

            if not best_container:
                continue

            text = best_text

            text = re.sub(r"\n+", "\n", text)
            text = text.strip()

            lines = [x.strip() for x in text.split("\n") if x.strip()]

            filtered = []

            for line in lines:
                if line not in filtered:
                    filtered.append(line)

            text = "\n".join(filtered)

            if len(text) < 20:
                continue

            post_id = get_post_id(url, text)

            image_url = None

            images = best_container.locator("img")
            image_count = images.count()

            for j in range(image_count):
                try:
                    src = images.nth(j).get_attribute("src")

                    if src and "fbcdn.net" in src:
                        image_url = src
                        break
                except:
                    pass

            print("Found post:", post_id)
            print("Post text:", text[:500])
            print("Post URL:", url)

            posts.append({
                "id": post_id,
                "url": url,
                "text": text,
                "image": image_url
            })

        except Exception as e:
            print("Error processing post:", e)

    return posts

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

    page.mouse.wheel(0, 2500)
    page.wait_for_timeout(5000)

    state = load_state()
    known_posts = set(state.get("posts", []))

    posts = extract_posts(page)

    print("Posts extracted:", len(posts))

    new_posts = []

    for post in posts:
        if post["id"] not in known_posts:
            new_posts.append(post)

    print("New posts:", len(new_posts))

    for post in reversed(new_posts):
        print("Sending:", post["url"])

        success = send_to_discord(
            post["text"],
            post["url"],
            post["image"]
        )

        if success:
            known_posts.add(post["id"])

    state["posts"] = list(known_posts)[-100:]

    save_state(state)

    browser.close()

print("Done.")
