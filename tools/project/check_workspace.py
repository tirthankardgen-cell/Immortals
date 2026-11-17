"""Check project navigation and optionally verify a dated organization record."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
MASTER = "docs/planning/IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md"
COMPONENT_ENTRYPOINTS = (
    "Sender/main.py",
    "Receiver/main.py",
    "Sender_v2/main.py",
    "Receiver_v2/main.py",
    "Speech_Test_Phase3/speech_test.py",
    "Website/package.json",
)
LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>\n]*>|[^)\n]*)\)")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")


def workspace_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if path == ROOT or not path.is_relative_to(ROOT):
        raise ValueError(f"Path is outside the workspace: {relative}")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def document_text(path: Path) -> str:
    """Exclude fenced examples and dated embedded source from link navigation."""
    output = []
    active_fence = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = FENCE.match(line)
        if active_fence:
            if match and match[1][0] == active_fence[0] and len(match[1]) >= len(active_fence) and not match[2].strip():
                active_fence = None
            continue
        if match:
            active_fence = match[1]
        else:
            output.append(line)
    return "\n".join(output)


def check_links(errors: list[str]) -> dict:
    documents = [
        ROOT / name for name in (
            "README.md", "AGENTS.md", "Website/README.md", "Website/AGENTS.md",
            "artifacts/README.md", "archive/README.md", "tools/project/README.md",
            "artifacts/validation/BOM_RESEARCH_2026-11-16.md",
            "artifacts/validation/PURCHASE_BOM_2026-11-16.md",
        )
    ]
    documents.extend(sorted((ROOT / "docs").rglob("*.md")))
    documents.extend(sorted((ROOT / "Website/docs").rglob("*.md")))
    local_links = 0
    for document in documents:
        if not document.is_file():
            errors.append(f"Missing documentation: {document.relative_to(ROOT).as_posix()}")
            continue
        for match in LINK.finditer(document_text(document)):
            target = match[1].strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            else:
                target = re.split(r'\s+["\']', target, maxsplit=1)[0]
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("//"):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            local_links += 1
            resolved = (document.parent / target).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                errors.append(f"Broken local link in {document.relative_to(ROOT).as_posix()}: {target}")
    return {"documents_checked": len(documents), "local_links_checked": local_links}


def verify_file(relative: str, expected: str, errors: list[str]) -> None:
    path = workspace_path(relative)
    if not path.is_file():
        errors.append(f"Missing preserved file: {relative}")
    elif sha256(path) != expected:
        errors.append(f"SHA-256 differs from the recorded snapshot: {relative}")


def check_record(relative: str, errors: list[str]) -> dict:
    manifest = json.loads(workspace_path(relative).read_text(encoding="utf-8-sig"))
    if manifest.get("schema_version") != 1 or manifest.get("state") not in {"applied", "verified"}:
        errors.append("Organization record must have schema_version 1 and an applied or verified state.")
    edits = {item["target"]: item for item in manifest["document_edits"]}
    for item in manifest["moved_files"]:
        if item["target"] in edits:
            # Navigation edits are permitted only with a preserved original.
            verify_file(edits[item["target"]]["backup"], item["sha256"], errors)
        else:
            verify_file(item["target"], item["sha256"], errors)
    for item in manifest["protected_files"]:
        verify_file(item["path"], item["sha256"], errors)
    for item in manifest["document_edits"]:
        verify_file(item["backup"], item["original_sha256"], errors)
        verify_file(item["target"], item["after_sha256"], errors)
    return {
        "move_operations": len(manifest["moves"]),
        "moved_files_checked": len(manifest["moved_files"]),
        "protected_files_checked": len(manifest["protected_files"]),
        "document_edits_checked": len(manifest["document_edits"]),
        "master_sha256": next(item["sha256"] for item in manifest["protected_files"] if Path(item["path"]).name == Path(MASTER).name),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", help="Workspace-relative organization manifest to verify")
    parser.add_argument("--report", help="Write JSON results to a workspace-relative path")
    args = parser.parse_args()
    errors: list[str] = []
    for name in (MASTER, ".gitmodules", "docs/development/development.md", "Website/docs/development.md", *COMPONENT_ENTRYPOINTS, "Website/.git"):
        if not workspace_path(name).exists():
            errors.append(f"Missing required project path: {name}")
    statistics = {"components_checked": len(COMPONENT_ENTRYPOINTS)}
    statistics.update(check_links(errors))
    if args.record:
        try:
            statistics.update(check_record(args.record, errors))
        except (OSError, ValueError, KeyError, StopIteration) as exc:
            errors.append(f"Organization record could not be verified: {exc}")
    report = {"passed": not errors, "statistics": statistics, "errors": errors}
    if args.report:
        report_path = workspace_path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
