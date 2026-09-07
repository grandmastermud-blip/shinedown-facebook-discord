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

    url = url.replace("&amp;", "&")

    match = re.search(
        r"https://www\.facebook\.com/Shinedown/posts/pfbid[a-zA-Z0-9]+",
        url
    )

    if match:
        return match.group(0)

    return None

def get_post_id(url, text):
    if url:
        match = re.search(r"pfbid[a-zA-Z0-9]+", url)

        if match:
            return match.group(0)

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()[:20]

def clean_post_text(text):
    text = text.replace("\ufeff", "")
    text = text.replace("\u00a0", " ")

    cutoff_markers = [
        "All reactions:",
        "Like\nComment",
        "Like\nComment\nShare",
        "View more comments",
        "Top fan"
    ]

    for marker in cutoff_markers:
        if marker in text:
            text = text.split(marker, 1)[0]

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if line == "Shinedown":
            continue

        if line == "·":
            continue

        if re.match(r"^\d+[smhdwy]$", line):
            continue

        if line.startswith("All reactions"):
            continue

        if line in ["Like", "Comment", "Share"]:
            continue

        if line == "See more":
            continue

        if line == "See less":
            continue

        if line == "…":
            continue

        lines.append(line)

    while lines and lines[0] in ["Young Again", "Shinedown", "·"]:
        lines.pop(0)

    text = "\n".join(lines)

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

def find_post_links(page):
    for attempt in range(3):
        print("Searching for Facebook post links, attempt", attempt + 1)

        links = page.locator("a[href*='/posts/pfbid']")
        count = links.count()

        print("Post links found:", count)

        if count > 0:
            return links

        page.wait_for_timeout(5000)

        page.reload(
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(10000)

        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(5000)

    return page.locator("a[href*='/posts/pfbid']")

def extract_posts(page):
    posts = []

    links = find_post_links(page)
    count = links.count()

    print("Final post link count:", count)

    seen = set()

    for i in range(count):
        try:
            link = links.nth(i)

            href = link.get_attribute("href")
            url = clean_url(href)

            if not url:
                continue

            if url in seen:
                continue

            seen.add(url)

            container = link
            best_text = ""
            best_container = None

            for level in range(1, 16):
                try:
                    container = container.locator("..")

                    text = container.inner_text(
                        timeout=2000
                    ).strip()

                    if len(text) > len(best_text) and len(text) < 15000:
                        best_text = text
                        best_container = container

                except:
                    break

            if not best_container:
                continue

            text = clean_post_text(best_text)

            if len(text) < 10:
                continue

            post_id = get_post_id(url, text)

            image_url = None

            images = best_container.locator("img")

            for j in range(images.count()):
                try:
                    image = images.nth(j)
                    src = image.get_attribute("src")

                    if not src:
                        continue

                    if "fbcdn.net" not in src:
                        continue

                    if "emoji" in src.lower():
                        continue

                    if "static.xx.fbcdn.net" in src:
                        continue

                    width = image.get_attribute("width")
                    height = image.get_attribute("height")

                    if width and height:
                        try:
                            if int(width) < 100 or int(height) < 100:
                                continue
                        except:
                            pass

                    image_url = src
                    break

                except:
                    pass

            title = "Shinedown posted on Facebook"

            first_line = text.split("\n")[0].strip()

            if len(first_line) <= 100 and (
                "!" in first_line
                or "?" in first_line
                or '"' in first_line
                or "'" in first_line
            ):
                title = first_line

                remaining = text.split("\n", 1)

                if len(remaining) > 1:
                    text = remaining[1].strip()

            print("Found post:", post_id)
            print("Title:", title)
            print("Text:", text[:500])
            print("Image:", image_url)

            posts.append({
                "id": post_id,
                "url": url,
                "title": title,
                "text": text,
                "image": image_url
            })

        except Exception as e:
            print("Error processing post:", e)

    return posts

def send_to_discord(post):
    text = post["text"]

    if len(text) > 3900:
        text = text[:3897] + "..."

    embed = {
        "title": post["title"],
        "description": text,
        "url": post["url"],
        "author": {
            "name": "Shinedown"
        },
        "footer": {
            "text": "Facebook • Shinedown"
        }
    }

    if post["image"]:
        embed["image"] = {
            "url": post["image"]
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

        success = send_to_discord(post)

        if success:
            known_posts.add(post["id"])

    state["posts"] = list(known_posts)[-100:]

    save_state(state)

    browser.close()

print("Done.")
