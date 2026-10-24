#!/usr/bin/env python3
"""
🛡️ GitHub Bounty Scanner — Powered by Doomsday Network & BountyGuard
====================================================================
Scans live GitHub bounty issues and highlights verified on‑chain escrowed
bounties while flagging known scraper honeypots.
"""

import json
import sys
import urllib.error
import urllib.request
from typing import List

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
KNOWN_BAD_ACTORS = {
    "zhangjiayang6835-cyber/bounty-plaza",
    "securebananalabs/bug-bounty",
    "ikalus1988/misakanet",
    "bujiproject-art/agentmidasopendevteam",
    "alfrexo95/bounty-bot",
}

VERIFIED_ESCROW_ORGS = {"doomsday-network"}

GITHUB_API_URL = "https://api.github.com/search/issues"
USER_AGENT = "DoomsdayBountyScanner/1.1"
DEFAULT_LIMIT = 15
TIMEOUT = 10  # seconds


# --------------------------------------------------------------------------- #
# Helper Functions
# --------------------------------------------------------------------------- #
def build_query(limit: int) -> str:
    """
    Build the GitHub Search API query URL.
    """
    query = (
        f"is:issue is:open label:bounty "
        f"sort:updated order:desc per_page={limit}"
    )
    return f"{GITHUB_API_URL}?q={urllib.parse.quote(query)}"


def fetch_json(url: str) -> dict:
    """
    Perform a GET request and return the parsed JSON payload.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        sys.stderr.write(f"❌ HTTP error {exc.code}: {exc.reason}\n")
        sys.exit(1)
    except urllib.error.URLError as exc:
        sys.stderr.write(f"❌ URL error: {exc.reason}\n")
        sys.exit(1)
    except json.JSONDecodeError:
        sys.stderr.write("❌ Failed to decode JSON response.\n")
        sys.exit(1)


def parse_repo_full(repo_url: str) -> str:
    """
    Extract the `<owner>/<repo>` part from a repository API URL.
    """
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        return ""
    return f"{parts[-2]}/{parts[-1]}"


def evaluate_issue(repo_full: str, owner: str) -> str:
    """
    Return a verdict string based on known bad actors or escrow verification.
    """
    repo_lc = repo_full.lower()
    owner_lc = owner.lower()
    if repo_lc in KNOWN_BAD_ACTORS:
        return "🔴 QUARANTINE (Known Scraper Trap)"
    elif owner_lc in VERIFIED_ESCROW_ORGS:
        return "🟢 SAFE_WITH_ESCROW (Verified L1 + Base Mainnet Reserve)"
    else:
        return "🟡 SAFE_NO_ESCROW (Unverified / Manual Maintainer Payout)"


def format_issue(item: dict) -> str:
    """
    Produce a human‑readable multiline string for a single issue.
    """
    repo_url = item.get("repository_url", "")
    repo_full = parse_repo_full(repo_url)
    owner = repo_full.split("/")[0] if "/" in repo_full else ""
    num = item.get("number", "N/A")
    title = item.get("title", "")[:75]
    verdict = evaluate_issue(repo_full, owner)

    lines = [
        f"  [{verdict}]",
        f"    -> {repo_full}#{num}: {title}",
        f"    -> URL: {item.get('html_url')}",
    ]
    return "\n".join(lines)


def scan_live_bounties(limit: int = DEFAULT_LIMIT) -> List[str]:
    """
    Query GitHub, evaluate each issue, and return a list of formatted strings.
    """
    print("🛡️ Scanning live GitHub issues with label:bounty ...")
    url = build_query(limit)
    data = fetch_json(url)

    total = data.get("total_count", 0)
    print(f"Found {total} open bounty issues. Auditing top {limit}:\n")

    formatted = []
    for item in data.get("items", []):
        formatted.append(format_issue(item))
    return formatted


# --------------------------------------------------------------------------- #
# Main Entry Point
# --------------------------------------------------------------------------- #
def main() -> None:
    limit = DEFAULT_LIMIT
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            sys.stderr.write("⚠️ Invalid limit argument, using default.\n")
    for block in scan_live_bounties(limit):
        print(block + "\n")


if __name__ == "__main__":
    main()