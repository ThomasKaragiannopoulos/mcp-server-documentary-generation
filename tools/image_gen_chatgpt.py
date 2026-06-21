"""
ChatGPT image generation tool — Playwright browser automation.
Uses DALL-E 3 via ChatGPT UI (requires ChatGPT Plus).

First run: opens browser for manual login, saves session to auth/chatgpt.json.
Subsequent runs: reuses saved session (headless).
Skips scenes that already have image.png (checkpointing).

Usage:
    py -m tools.image_gen_chatgpt generated/<title>/scenes.json --title "Title"
"""

import os
import sys
import json
import time
import argparse
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from tools.project import scene_paths

sys.stdout.reconfigure(encoding="utf-8")

AUTH_FILE = "auth/chatgpt.json"
CHATGPT_URL = "https://chatgpt.com"
GENERATION_TIMEOUT = 180_000  # 3 min — DALL-E can be slow under load


def _get_context(playwright, headless: bool):
    browser = playwright.chromium.launch(headless=headless, slow_mo=50)
    if os.path.exists(AUTH_FILE):
        context = browser.new_context(storage_state=AUTH_FILE)
    else:
        context = browser.new_context()
    return browser, context


def ensure_auth():
    """First-run login flow. Opens browser, waits for manual login, saves session."""
    os.makedirs("auth", exist_ok=True)
    print("No saved session found. Opening browser for manual login...")
    print("Log in to ChatGPT, then come back here and press Enter.")

    with sync_playwright() as p:
        browser, context = _get_context(p, headless=False)
        page = context.new_page()
        page.goto(CHATGPT_URL)
        input("\nPress Enter after you have logged in: ")
        context.storage_state(path=AUTH_FILE)
        print(f"Session saved → {AUTH_FILE}")
        browser.close()


def _wait_for_image(page) -> str:
    """Poll for a completed DALL-E image URL in the last assistant message.
    Returns the CDN src once it resolves from blob to https."""
    deadline = time.time() + GENERATION_TIMEOUT / 1000
    while time.time() < deadline:
        imgs = page.locator("[data-message-author-role='assistant'] img").all()
        for img in reversed(imgs):
            try:
                src = img.get_attribute("src") or ""
                if src.startswith("https://") and ("oaiusercontent" in src or "oaidalleresp" in src):
                    return src
            except Exception:
                pass
        time.sleep(2)
    raise TimeoutError("Timed out waiting for DALL-E image URL")


def _generate_one(page, prompt: str) -> bytes:
    """Navigate to new chat, send prompt, wait for image, return PNG bytes."""
    page.goto(CHATGPT_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Find input — try multiple selectors for resilience
    input_box = (
        page.locator("#prompt-textarea").first
        if page.locator("#prompt-textarea").count()
        else page.get_by_role("textbox").first
    )
    input_box.wait_for(state="visible", timeout=15_000)
    input_box.click()
    input_box.fill(prompt)
    page.keyboard.press("Enter")

    print("    Waiting for DALL-E 3 generation...", flush=True)
    src = _wait_for_image(page)

    # Download image bytes via Playwright's request context (inherits cookies)
    response = page.request.get(src)
    if not response.ok:
        raise RuntimeError(f"Image download failed: {response.status}")
    return response.body()


def process_batch(storyboard_path: str, title: str):
    with open(storyboard_path, encoding="utf-8") as f:
        scenes = json.load(f)

    pending = []
    for scene in scenes:
        paths = scene_paths(title, scene["id"])
        if os.path.exists(paths["image"]):
            print(f"[{scene['id']}] Skipping — image already exists")
        elif not scene.get("image_prompt"):
            print(f"[{scene['id']}] Skipping — no image_prompt")
        else:
            pending.append((scene, paths))

    if not pending:
        print("All scenes already generated.")
        return scenes

    if not os.path.exists(AUTH_FILE):
        ensure_auth()

    with sync_playwright() as p:
        browser, context = _get_context(p, headless=True)
        page = context.new_page()

        for scene, paths in pending:
            print(f"\n[{scene['id']}] {scene['section']}")
            print(f"    Prompt: {scene['image_prompt'][:80]}...")

            try:
                img_bytes = _generate_one(page, scene["image_prompt"])
                os.makedirs(paths["dir"], exist_ok=True)
                with open(paths["image"], "wb") as f:
                    f.write(img_bytes)
                scene["image_path"] = paths["image"]
                print(f"    Saved {paths['image']}")
            except (TimeoutError, PWTimeout) as e:
                print(f"    [!] Timed out on scene {scene['id']} — skipping: {e}")
            except Exception as e:
                print(f"    [!] Error on scene {scene['id']}: {e}")

            # Small gap between scenes to avoid triggering rate limits
            time.sleep(3)

        # Refresh saved session before closing
        context.storage_state(path=AUTH_FILE)
        browser.close()

    with open(storyboard_path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(pending)} images generated via ChatGPT DALL-E 3.")
    return scenes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChatGPT DALL-E 3 image generation via Playwright")
    parser.add_argument("storyboard", help="Path to scenes.json")
    parser.add_argument("--title", required=True, help="Documentary title")
    parser.add_argument("--login", action="store_true", help="Force re-login (clear saved session)")
    args = parser.parse_args()

    if args.login and os.path.exists(AUTH_FILE):
        os.remove(AUTH_FILE)
        print("Cleared saved session.")

    process_batch(args.storyboard, args.title)
