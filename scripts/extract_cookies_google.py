#!/usr/bin/env python3
"""
Cookie Extraction Helper for Pipedream (Google SSO compatible)

Uses a persistent browser profile to handle Google SSO properly.
"""

import asyncio
import base64
import json
import sys
import time
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwright not installed. Run: pip install playwright")
    sys.exit(1)


async def extract_cookies():
    """Open browser with persistent context for Google SSO."""
    tmp_dir = Path(".tmp")
    tmp_dir.mkdir(exist_ok=True)

    # Use persistent profile directory
    profile_dir = tmp_dir / "browser_profile"
    profile_dir.mkdir(exist_ok=True)

    signal_file = tmp_dir / "logged_in"
    if signal_file.exists():
        signal_file.unlink()

    async with async_playwright() as p:
        # Launch with persistent context - this helps with Google SSO
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            viewport={"width": 1280, "height": 800},
            # These args help with Google SSO
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        print("\nOpening Pipedream login page...")
        await page.goto("https://pipedream.com/auth/login")

        print("\n" + "=" * 60)
        print("INSTRUCTIONS:")
        print("=" * 60)
        print("1. Click 'Sign in with Google' and complete login")
        print("2. Navigate to any workflow to ensure full auth")
        print("3. Run in another terminal: touch .tmp/logged_in")
        print("=" * 60)
        print("\nWaiting for signal file...")

        # Wait for signal
        max_wait = 300
        waited = 0
        while not signal_file.exists() and waited < max_wait:
            await asyncio.sleep(2)
            waited += 2
            if waited % 30 == 0:
                print(f"  Still waiting... ({waited}s)")

        if not signal_file.exists():
            print("\nTimeout! Run: touch .tmp/logged_in")
            await context.close()
            return

        print("\nExtracting cookies...")
        await asyncio.sleep(2)

        cookies = await context.cookies()
        pipedream_cookies = [
            c for c in cookies
            if "pipedream.com" in c.get("domain", "")
        ]

        if not pipedream_cookies:
            print("\nERROR: No Pipedream cookies found!")
            await context.close()
            return

        cookie_data = []
        for c in pipedream_cookies:
            cookie_data.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c.get("path", "/"),
                "expires": c.get("expires", -1),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", True),
                "sameSite": c.get("sameSite", "Lax"),
            })

        cookies_json = json.dumps(cookie_data, indent=2)
        cookies_b64 = base64.b64encode(cookies_json.encode()).decode()

        # Save files
        (tmp_dir / "cookies.json").write_text(cookies_json)
        (tmp_dir / "cookies_base64.txt").write_text(cookies_b64)

        print("\n" + "=" * 60)
        print(f"SUCCESS! {len(pipedream_cookies)} cookies extracted.")
        print("=" * 60)

        now = time.time()
        for c in cookie_data:
            if c["expires"] > 0:
                days = (c["expires"] - now) / 86400
                print(f"  {c['name']}: {days:.1f} days left")

        print("\n" + "=" * 60)
        print("PIPEDREAM_COOKIES:")
        print("=" * 60)
        print(cookies_b64)
        print("=" * 60)

        if signal_file.exists():
            signal_file.unlink()

        await context.close()
        return cookies_b64


if __name__ == "__main__":
    print("=" * 60)
    print("Pipedream Cookie Extraction (Google SSO compatible)")
    print("=" * 60)
    try:
        asyncio.run(extract_cookies())
    except KeyboardInterrupt:
        print("\nCancelled.")
