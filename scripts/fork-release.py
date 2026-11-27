"""Publish the verified Windows and Apple Silicon Core archives."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True).strip()


def publish():
    repo = os.environ["GITHUB_REPOSITORY"]
    commit = os.environ["GITHUB_SHA"]
    branch = os.environ["GITHUB_REF_NAME"]
    build = int(os.environ["GITHUB_RUN_NUMBER"])
    tag = f"fork-{build}"
    api = f"repos/{repo}"

    def branch_head():
        return gh("api", f"{api}/git/ref/heads/{branch}", "--jq", ".object.sha")

    if branch_head() != commit:
        print(f"Skipping {tag}: {branch} has moved past {commit}.")
        return

    releases = gh(
        "api", "--paginate", f"{api}/releases?per_page=100",
        "--jq", '.[] | select(.tag_name | test("^fork-[1-9][0-9]*$")) | {tag_name, draft, target_commitish}',
    )
    records = [json.loads(line) for line in releases.splitlines()]
    if any(not record["draft"] and int(record["tag_name"].removeprefix("fork-")) >= build for record in records):
        print(f"Skipping {tag}: this or a newer build is already published.")
        return
    draft = next((record for record in records if record["tag_name"] == tag), None)
    if draft and draft["target_commitish"] != commit:
        raise RuntimeError(f"Draft {tag} targets a different commit.")

    dist = Path("dist")
    archive_names = {
        "macos-aarch64": "herdr-core-macos-aarch64.tar.gz",
        "windows-x86_64": "herdr-core-windows-x86_64.zip",
    }
    result = subprocess.check_output(
        [sys.executable, "scripts/manifest", str(dist)],
        env={**os.environ, "HERDR_CORE_FORK_BUILD": str(build)},
    )
    manifest = json.loads(result)
    if set(manifest["targets"]) != set(archive_names):
        raise RuntimeError("Expected exactly the Windows x64 and Apple Silicon Core packages.")
    files = {dist / name: manifest["targets"][target]["sha256"] for target, name in archive_names.items()}
    sums = dist / "SHA256SUMS"
    sums.write_text("".join(f"{digest}  {path.name}\n" for path, digest in files.items()), encoding="ascii")
    document = dist / "manifest.json"
    document.write_bytes(result)
    for path in (sums, document):
        files[path] = hashlib.sha256(path.read_bytes()).hexdigest()

    if draft is None:
        repo_url = f"{os.environ['GITHUB_SERVER_URL']}/{repo}"
        print(gh(
            "release", "create", tag, "--repo", repo, "--target", commit, "--draft",
            "--title", f"Herdr Core personal fork {manifest['version']}",
            "--notes", (
                f"Windows x64 and Apple Silicon Core from [`{commit[:7]}`]({repo_url}/commit/{commit}). "
                f"[Build run]({repo_url}/actions/runs/{os.environ['GITHUB_RUN_ID']})"
            ),
        ))
    gh("release", "upload", tag, *(str(path) for path in files), "--repo", repo, "--clobber")
    release = json.loads(gh(
        "release", "view", tag, "--repo", repo, "--json", "databaseId,isDraft,targetCommitish",
    ))
    if not release["isDraft"] or release["targetCommitish"] != commit:
        raise RuntimeError(f"Release {tag} is no longer the expected draft.")
    assets = json.loads(gh("api", f"{api}/releases/{release['databaseId']}/assets"))
    uploaded = {asset["name"]: asset["digest"] for asset in assets if asset["state"] == "uploaded"}
    if uploaded != {path.name: f"sha256:{digest}" for path, digest in files.items()}:
        raise RuntimeError(f"Release {tag} has missing, unexpected, or different assets.")
    if branch_head() != commit:
        print(f"Keeping {tag} as a draft: {branch} advanced during the upload.")
        return
    print(gh("release", "edit", tag, "--repo", repo, "--draft=false", "--latest"))


if __name__ == "__main__":
    publish()
