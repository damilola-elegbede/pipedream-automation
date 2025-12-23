#!/usr/bin/env python3
"""
Cookie Extraction Helper for Pipedream

This script helps extract authentication cookies from a logged-in
Pipedream session for use in automated deployments.

Usage:
    1. Run this script: python scripts/extract_cookies.py
    2. Log into Pipedream in the browser that opens
    3. Navigate to any workflow page
    4. Press Enter in the terminal
    5. Copy the base64-encoded cookie string
    6. Add to GitHub Secrets as PIPEDREAM_COOKIES

Note: Cookies typically expire after 30 days. Set a reminder to refresh.
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
    """Open browser, let user login, and extract cookies."""
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
            print("3. Return to this terminal and press Enter")
            print("=" * 60 + "\n")

            input("Press Enter after logging in... ")

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

            # Save locally for testing
            tmp_dir = Path(".tmp")
            tmp_dir.mkdir(exist_ok=True)
            cookies_file = tmp_dir / "cookies.json"
            with open(cookies_file, "w") as f:
                f.write(cookies_json)

            print("\n" + "=" * 60)
            print("SUCCESS! Cookies extracted.")
            print("=" * 60)
            print(f"\nCookies found: {len(pipedream_cookies)}")
            print(f"Saved to: {cookies_file}")

            # Check expiration
            now = time.time()
            for c in cookie_data:
                if c["expires"] > 0:
                    days_left = (c["expires"] - now) / 86400
                    print(f"  - {c['name']}: expires in {days_left:.1f} days")

            print("\n" + "=" * 60)
            print("BASE64-ENCODED COOKIES (for GitHub Secrets):")
            print("=" * 60)
            print(cookies_b64)
            print("=" * 60)

            print("\nNext steps:")
            print("1. Copy the base64 string above")
            print("2. Go to: GitHub repo > Settings > Secrets > Actions")
            print("3. Add new secret: PIPEDREAM_COOKIES")
            print("4. Paste the base64 string as the value")
            print("\nFor local testing, set environment variable:")
            print(f"  export PIPEDREAM_COOKIES=$(cat {cookies_file} | base64)")
        finally:
            await browser.close()


def main():
    """Entry point."""
    print("=" * 60)
    print("Pipedream Cookie Extraction Tool")
    print("=" * 60)

    try:
        asyncio.run(extract_cookies())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)


if __name__ == "__main__":
    main()
