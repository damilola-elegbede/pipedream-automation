#!/usr/bin/env python3
"""
Cookie Extraction Helper for Pipedream (Auto-wait version)

This version waits for a signal file instead of keyboard input,
making it suitable for use in automated environments.

Usage:
    1. Run this script: python scripts/extract_cookies_auto.py
    2. Log into Pipedream in the browser that opens
    3. Navigate to any workflow page
    4. Create the signal file: touch .tmp/logged_in
    5. Cookies will be extracted automatically
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
    print("Then run: playwright install chromium")
    sys.exit(1)


async def extract_cookies():
    """Open browser, wait for signal file, and extract cookies."""
    # Ensure .tmp directory exists
    tmp_dir = Path(".tmp")
    tmp_dir.mkdir(exist_ok=True)

    # Signal file path
    signal_file = tmp_dir / "logged_in"

    # Remove old signal file if exists
    if signal_file.exists():
        signal_file.unlink()

    async with async_playwright() as p:
        # Launch visible browser for login
        browser = await p.chromium.launch(headless=False)
        try:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()

            # Navigate to Pipedream login
            print("\nOpening Pipedream login page...")
            await page.goto("https://pipedream.com/auth/login")

            print("\n" + "=" * 60)
            print("INSTRUCTIONS:")
            print("=" * 60)
            print("1. Log into Pipedream in the browser window")
            print("2. Navigate to any workflow to ensure full authentication")
            print("3. In another terminal, run: touch .tmp/logged_in")
            print("=" * 60)
            print("\nWaiting for signal file (.tmp/logged_in)...")

            # Wait for signal file (check every 2 seconds, timeout after 5 minutes)
            max_wait = 300  # 5 minutes
            waited = 0
            while not signal_file.exists() and waited < max_wait:
                await asyncio.sleep(2)
                waited += 2
                if waited % 30 == 0:
                    print(f"  Still waiting... ({waited}s elapsed)")

            if not signal_file.exists():
                print("\nERROR: Timeout waiting for signal file!")
                print("Make sure to run: touch .tmp/logged_in")
                return

            print("\nSignal received! Extracting cookies...")

            # Small delay to ensure page is fully loaded
            await asyncio.sleep(2)

            # Extract cookies
            cookies = await context.cookies()

            # Filter to Pipedream cookies only
            pipedream_cookies = [
                c for c in cookies
                if "pipedream.com" in c.get("domain", "")
            ]

            if not pipedream_cookies:
                print("\nERROR: No Pipedream cookies found!")
                print("Make sure you logged in successfully.")
                return

            # Prepare cookies for storage (only essential fields)
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

            # Encode as base64
            cookies_json = json.dumps(cookie_data, indent=2)
            cookies_b64 = base64.b64encode(cookies_json.encode()).decode()

            # Save locally
            cookies_file = tmp_dir / "cookies.json"
            with open(cookies_file, "w") as f:
                f.write(cookies_json)

            # Save base64 version
            cookies_b64_file = tmp_dir / "cookies_base64.txt"
            with open(cookies_b64_file, "w") as f:
                f.write(cookies_b64)

            print("\n" + "=" * 60)
            print("SUCCESS! Cookies extracted.")
            print("=" * 60)
            print(f"\nCookies found: {len(pipedream_cookies)}")
            print(f"Saved JSON to: {cookies_file}")
            print(f"Saved base64 to: {cookies_b64_file}")

            # Check expiration
            now = time.time()
            for c in cookie_data:
                if c["expires"] > 0:
                    days_left = (c["expires"] - now) / 86400
                    print(f"  - {c['name']}: expires in {days_left:.1f} days")

            print("\n" + "=" * 60)
            print("PIPEDREAM_COOKIES value:")
            print("=" * 60)
            print(cookies_b64)
            print("=" * 60)

            # Clean up signal file
            if signal_file.exists():
                signal_file.unlink()

            return cookies_b64
        finally:
            await browser.close()


def main():
    """Entry point."""
    print("=" * 60)
    print("Pipedream Cookie Extraction Tool (Auto-wait version)")
    print("=" * 60)

    try:
        result = asyncio.run(extract_cookies())
        if result:
            print("\nDone! You can now set the GitHub secret.")
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)


if __name__ == "__main__":
    main()
