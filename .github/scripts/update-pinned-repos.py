import json
import os
import re
import urllib.error
import urllib.request

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_PAT", "")
README_PATH = "README.md"

QUERY = """
{
  viewer {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          url
          stargazerCount
          forkCount
          primaryLanguage {
            name
          }
        }
      }
    }
  }
}
"""


def fetch_pinned_repos():
    if not GITHUB_TOKEN:
        raise RuntimeError("Missing GitHub token. Set GITHUB_TOKEN or GH_PAT in the workflow environment.")

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API request failed with status {exc.code}: {exc.reason}. "
            f"Check that the token is valid and has access to the repository/user data. Response: {body}"
        ) from exc

    viewer = data.get("data", {}).get("viewer")
    if not viewer:
        raise RuntimeError(f"GitHub API response did not include viewer data: {data}")

    return viewer.get("pinnedItems", {}).get("nodes", [])


def build_markdown(repos):
    if not repos:
        return "No pinned repositories found.\n"

    lines = []
    for repo in repos:
        name = repo["name"]
        url = repo["url"]
        desc = repo.get("description") or "No description"
        lang = (repo.get("primaryLanguage") or {}).get("name", "")
        stars = repo.get("stargazerCount", 0)
        forks = repo.get("forkCount", 0)

        lang_badge = f" `{lang}`" if lang else ""
        lines.append(f"- [**{name}**]({url}){lang_badge} — {desc} | :star: {stars} :fork_and_knife: {forks}")

    return "\n".join(lines) + "\n"


def update_readme(section_md):
    with open(README_PATH, "r") as f:
        content = f.read()

    pattern = r"(<!-- PINNED-REPOS:START -->)\n.*?(<!-- PINNED-REPOS:END -->)"
    replacement = rf"\1\n{section_md}\2"
    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open(README_PATH, "w") as f:
        f.write(updated)


if __name__ == "__main__":
    repos = fetch_pinned_repos()
    md = build_markdown(repos)
    update_readme(md)
    print(f"Updated README with {len(repos)} pinned repos.")
