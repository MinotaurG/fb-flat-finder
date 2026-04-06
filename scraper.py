# scraper.py
import json
import asyncio
import logging
import yaml
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from parser_cascade import parse_listing_cascade as parse_listing
from db import get_conn, insert_listing

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

COOKIES_FILE = "cookies.json"
GROUPS_FILE = "groups.yaml"
SCROLL_COUNT = 10
OUTPUT_FILE = "listings.json"


def load_groups():
    with open(GROUPS_FILE, "r") as f:
        config = yaml.safe_load(f)
    return config.get("groups", [])


async def load_cookies(context):
    path = Path(COOKIES_FILE)
    if not path.exists():
        raise FileNotFoundError(f"{COOKIES_FILE} not found. Export your Facebook cookies first.")
    with open(path, "r") as f:
        cookies = json.load(f)
    await context.add_cookies(cookies)


async def expand_see_more(page):
    """Click See more buttons one at a time, max 10 per scroll."""
    for _ in range(10):
        btn = await page.query_selector('div[role="button"]:has-text("See more")')
        if not btn:
            break
        try:
            await btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)
            await btn.click(force=True)
            await page.wait_for_timeout(500)
        except Exception:
            break


async def scroll_and_collect(page):
    seen = set()
    posts = []
    for i in range(SCROLL_COUNT):
        await page.wait_for_timeout(2000)
        await expand_see_more(page)

        # Collect images and post URLs grouped by post
        post_meta = await page.evaluate("""
            () => {
                const msgs = document.querySelectorAll('div[data-ad-rendering-role="story_message"]');
                return Array.from(msgs).map(msg => {
                    const article = msg.closest('div[role="article"]') || msg.parentElement?.parentElement?.parentElement;

                    // Images
                    const imgs = article ? article.querySelectorAll('img[src*="scontent"]') : [];
                    const images = Array.from(imgs)
                        .map(img => img.src)
                        .filter(src => !src.includes('emoji') && !src.includes('50x50') && !src.includes('36x36'));

                    // Post URL - look for any post link
                    let postUrl = null;
                    if (article) {
                        const links = article.querySelectorAll('a[href]');
                        for (const link of links) {
                            const h = link.href;
                            if (h.includes('/posts/') || h.includes('/permalink/') || h.includes('story_fbid') || h.includes('?comment_id')) {
                                postUrl = h.split('?')[0];
                                break;
                            }
                        }
                    }

                    return { images, postUrl };
                });
            }
        """)

        elements = await page.query_selector_all('div[data-ad-rendering-role="story_message"]')
        for idx, el in enumerate(elements):
            text = (await el.inner_text()).strip()
            if not text or len(text) < 50:
                continue
            is_dup = any(
                text in s or s in text or
                text[:80] in s or s[:80] in text
                for s in seen
            )
            if not is_dup:
                seen.add(text)
                meta = post_meta[idx] if idx < len(post_meta) else {}
                posts.append({
                    "text": text,
                    "images": meta.get("images", []),
                    "post_url": meta.get("postUrl"),
                })
        log.info(f"  Scroll {i+1}/{SCROLL_COUNT}: {len(posts)} posts")
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
    return posts


async def scrape_group(page, group):
    url = group["url"]
    log.info(f"--- Scraping group: {group.get('name', url)} ---")
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    # Get actual group name from page
    name = await page.evaluate("""
        () => {
            const el = document.querySelector('h1 a') || document.querySelector('h1 span') || document.querySelector('h1');
            const text = el ? el.innerText.trim() : null;
            if (text && text.length > 2 && text !== 'Notifications') return text;
            return null;
        }
    """)
    if name:
        group["name"] = name

    posts = await scroll_and_collect(page)
    log.info(f"  [{group['name']}] {len(posts)} unique posts scraped")
    return posts


async def main():
    groups = load_groups()
    if not groups:
        log.error("No groups in groups.yaml")
        return

    log.info(f"Starting scraper with {len(groups)} groups")
    conn = get_conn()
    scraped_at = datetime.now().isoformat()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await load_cookies(context)
        page = await context.new_page()

        all_listings = []
        total_new = 0
        total_parsed = 0
        total_failed = 0

        for g_idx, group in enumerate(groups, 1):
            log.info(f"\nGroup {g_idx}/{len(groups)}: {group.get('name', group['url'])}")
            try:
                posts = await scrape_group(page, group)
            except Exception as e:
                log.error(f"  Failed to scrape: {e}")
                try:
                    await page.goto("about:blank")
                    await page.wait_for_timeout(1000)
                except Exception:
                    pass
                continue

            for i, post in enumerate(posts, 1):
                log.info(f"  [{i}/{len(posts)}] Parsing: {post['text'][:60]}...")
                parsed = parse_listing(post["text"])
                if parsed:
                    parsed["raw_text"] = post["text"]
                    parsed["images"] = post["images"]
                    parsed["post_url"] = post["post_url"]
                    parsed["scraped_at"] = scraped_at
                    all_listings.append(parsed)
                    total_parsed += 1
                    if insert_listing(conn, parsed, group["name"], group["url"]):
                        total_new += 1
                else:
                    total_failed += 1

            log.info(f"  Running total: {total_parsed} parsed | {total_new} new | {total_failed} failed")

        with open(OUTPUT_FILE, "w") as f:
            json.dump(all_listings, f, indent=2, ensure_ascii=False)

        conn.close()
        log.info(f"\n{'='*50}")
        log.info(f"DONE — Parsed: {total_parsed} | New in DB: {total_new} | Failed: {total_failed}")
        log.info(f"{'='*50}")
        await browser.close()


asyncio.run(main())
