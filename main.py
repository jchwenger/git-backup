"""Back up all public repositories of a user from GitHub, GitLab, or Codeberg."""

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

PLATFORM_APIS: dict[str, dict] = {
    "github.com": {
        "repos_url": "https://api.github.com/users/{user}/repos",
        "params": {"per_page": 100, "type": "owner"},
        "pagination": "page",
        "clone_key": "clone_url",
        "name_key": "name",
        "fork_key": "fork",
    },
    "gitlab.com": {
        "repos_url": "https://gitlab.com/api/v4/users/{user}/projects",
        "params": {"per_page": 100},
        "pagination": "page",
        "clone_key": "http_url_to_repo",
        "name_key": "path",
        "fork_key": None,
    },
    "codeberg.org": {
        "repos_url": "https://codeberg.org/api/v1/users/{user}/repos",
        "params": {"limit": 50},
        "pagination": "page",
        "clone_key": "clone_url",
        "name_key": "name",
        "fork_key": "fork",
    },
}


def parse_user_url(url: str) -> tuple[str, str]:
    """Extract (platform_host, username) from a profile URL."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.hostname
    if host is None:
        sys.exit(f"Error: could not parse host from '{url}'")

    parts = [p for p in parsed.path.strip("/").split("/") if p]

    if host == "gitlab.com" and len(parts) >= 2 and parts[0] == "users":
        username = parts[1]
        if len(parts) < 3 or parts[2] != "projects":
            print(f"Note: normalized GitLab URL to https://gitlab.com/users/{username}/projects")
    elif len(parts) >= 1:
        username = parts[0]
    else:
        sys.exit(f"Error: could not extract username from '{url}'")

    if host not in PLATFORM_APIS:
        sys.exit(f"Error: unsupported platform '{host}'. Supported: {', '.join(PLATFORM_APIS)}")

    return host, username


def fetch_repos(host: str, username: str, *, include_forks: bool = False) -> list[dict]:
    """Fetch all public repos via the platform's API, handling pagination."""
    cfg = PLATFORM_APIS[host]
    repos: list[dict] = []
    page = 1

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        while True:
            params = {**cfg["params"], cfg["pagination"]: page}
            headers = {"Accept": "application/json"}
            if host == "github.com":
                headers["X-GitHub-Api-Version"] = "2022-11-28"

            resp = client.get(cfg["repos_url"].format(user=username), params=params, headers=headers)
            if resp.status_code == 404:
                sys.exit(f"Error: user '{username}' not found on {host}")
            resp.raise_for_status()

            batch = resp.json()
            if not batch:
                break

            repos.extend(batch)
            page += 1

    if not include_forks and cfg["fork_key"]:
        repos = [r for r in repos if not r.get(cfg["fork_key"], False)]

    return repos


def clone_or_pull(clone_url: str, dest: Path) -> None:
    """Clone a repo, or pull if it already exists locally."""
    if dest.exists() and (dest / ".git").is_dir():
        print(f"  pulling  {dest.name} …", flush=True)
        subprocess.run(
            ["git", "-C", str(dest), "pull", "--ff-only"],
            check=False,
        )
    else:
        print(f"  cloning  {dest.name} …", flush=True)
        subprocess.run(
            ["git", "clone", "--quiet", clone_url, str(dest)],
            check=False,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="User profile URL (GitHub, GitLab, or Codeberg)")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("."),
        help="Parent directory for backups (default: current directory)",
    )
    parser.add_argument(
        "--include-forks",
        action="store_true",
        help="Also back up forked repositories",
    )
    args = parser.parse_args()

    host, username = parse_user_url(args.url)
    print(f"Platform : {host}")
    print(f"User     : {username}")

    cfg = PLATFORM_APIS[host]
    repos = fetch_repos(host, username, include_forks=args.include_forks)
    print(f"Repos    : {len(repos)}")

    if not repos:
        print("Nothing to back up.")
        return

    backup_dir: Path = args.output / username
    backup_dir.mkdir(parents=True, exist_ok=True)
    print(f"Dest     : {backup_dir.resolve()}\n")

    for repo in sorted(repos, key=lambda r: r[cfg["name_key"]].lower()):
        name = repo[cfg["name_key"]]
        clone_url = repo[cfg["clone_key"]]
        clone_or_pull(clone_url, backup_dir / name)

    print(f"\nDone — {len(repos)} repos backed up into {backup_dir.resolve()}")


if __name__ == "__main__":
    main()
