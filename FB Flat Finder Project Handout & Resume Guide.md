# FB Flat Finder Project Handout & Resume Guide

## 1. What We're Building

A tool that scrapes flat listings from multiple Facebook groups, filters them by your criteria (BHK, rent, area), and presents clean results — without manually checking each group.

**One-line problem statement:**  
"I want to see new flat listings from multiple Facebook groups, filtered by my criteria, without manually checking each group every day."

**Pipeline:**  
```
Input → Facebook group posts (public + private)  
Transform → AI parses BHK / rent / locality / contact  
Output → Filtered list of relevant flat listings  
Trigger → Run manually or on a schedule
```

## 2. Architecture & Design Decisions

The system is split into 4 loosely coupled modules (separation of concerns):

- **[Scraper]** → Playwright browser automation, logs into FB, scrolls group feed
- **[Parser]** → AI (Gemini Flash) extracts structured fields from raw post text
- **[Storage]** → SQLite local database stores posts and parsed results
- **[Output]** → Query/filter layer, later a simple UI or Telegram bot

**Key design principle:**  
*Loose coupling*: If Facebook changes its layout, you only fix the Scraper. If you switch from Gemini to Claude, you only touch the Parser. Nothing else breaks.

**Stack choices:**
- **Browser automation**: Playwright (async, modern, better than Selenium on JS-heavy sites)
- **AI parsing**: Gemini Flash (free tier, fast)
- **Database**: SQLite (zero setup, file-based, perfect for solo projects)
- **Language**: Python 3.10+
- **Auth method**: Cookies (not credentials) — avoids 2FA/captcha issues

## 3. MVP Scope

**MVP** = smallest thing that proves the full pipeline works end to end, manually triggered, for one group.

**MVP checklist:**
- [ ] Scrape one Facebook group → get raw post text
- [ ] Run posts through AI filter → structured fields
- [ ] Print relevant ones to terminal

*No UI, no scheduler, no database yet. That all comes after MVP validates the core idea.*

## 4. Project Structure

```
fb-flat-finder/
├── scraper.py        ← Step 1 (IN PROGRESS)
├── cookies.json      ← Your FB session (NEVER commit this)
├── requirements.txt
└── .gitignore
```

**.gitignore contents:**
```
cookies.json
__pycache__/
.env
```

## 5. Step 1 Status — Scraper Module

This is where we stopped. The `scraper.py` file was written and explained. The next action is to run it and report back what happens.

### Setup commands already done:
```bash
mkdir fb-flat-finder && cd fb-flat-finder
pip install playwright
playwright install chromium
```

### Cookie export steps:
1. Install Chrome extension: "Cookie-Editor" by cgagnier
2. Log into Facebook in Chrome
3. Open Cookie-Editor → Export → paste into `cookies.json`

### scraper.py — full code:
```python
import json
import asyncio
from playwright.async_api import async_playwright

# --- Config ---
GROUP_URL = "https://www.facebook.com/groups/YOUR_GROUP_ID"
COOKIES_FILE = "cookies.json"
SCROLL_COUNT = 5

async def load_cookies(context):
    with open(COOKIES_FILE, "r") as f:
        cookies = json.load(f)
    await context.add_cookies(cookies)

async def scroll_and_collect(page):
    posts = []
    for i in range(SCROLL_COUNT):
        await page.wait_for_timeout(2000)
        elements = await page.query_selector_all(
            '[data-ad-comet-preview="message"]'
        )
        for el in elements:
            text = await el.inner_text()
            if text and text not in posts:
                posts.append(text)
        print(f"Scroll {i+1}: {len(posts)} unique posts so far")
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
    return posts

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await load_cookies(context)
        page = await context.new_page()
        print("Navigating to group...")
        await page.goto(GROUP_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        posts = await scroll_and_collect(page)
        print(f"\n--- RESULTS: {len(posts)} posts found ---\n")
        for i, post in enumerate(posts, 1):
            print(f"[{i}] {post[:200]}")
            print("---")
        await browser.close()

asyncio.run(main())
```

## 6. CS Concepts Covered So Far

- **Separation of concerns**: Each module does one thing; changes are isolated
- **Loose coupling**: Modules don't know about each other's internals
- **Vertical slicing**: Build thin end-to-end slices, not full horizontal layers
- **async/await**: Non-blocking I/O — browser ops involve waiting; async lets program continue
- **SPAs vs static sites**: Facebook is JS-rendered; requests+BS4 won't work, need real browser
- **DOM querying**: `query_selector_all` with attribute selectors to find elements in page
- **Secrets management**: `.gitignore` keeps credentials out of version control
- **Cookies vs credentials**: Session tokens sidestep 2FA, captchas, and credential risk
- **MVP thinking**: Smallest proof of concept before adding complexity

## 7. How to Resume in a New Chat

Share this document with Claude and use the following prompt:

> I'm building a Facebook group scraper to find flat listings in Hyderabad. I'm learning CS concepts as we go. Here's my project handout with everything we've covered. We stopped at Step 1 (`scraper.py`). I've set up the project and installed Playwright. [paste result of running `scraper.py`, or describe the error you got]. Let's continue from here.

**Next steps after scraper works:**
1. **Step 2**: AI parsing layer — send post text to Gemini, extract BHK/rent/area/contact as JSON
2. **Step 3**: SQLite storage — persist posts, avoid re-processing duplicates  
3. **Step 4**: Filtering layer — query by your criteria
4. **Step 5**: Scheduler — run automatically once or twice a day