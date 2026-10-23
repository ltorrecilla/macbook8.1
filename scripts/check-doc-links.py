#!/usr/bin/env python3
"""Conservative, offline check of relative Markdown links and heading fragments.

Uses Python stdlib only, reads files, never changes them. Intentionally checks
inline Markdown links, not full Markdown reference-style links or HTML links.
"""
from __future__ import annotations

import pathlib
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.M)
EXPLICIT = re.compile(r"""<a\s+(?:[^>]*?\s)?(?:id|name)=["']([^"']+)["']""", re.I)


def anchor_slugs(text: str) -> set[str]:
    # GitHub-style heading slugs, including deduplication. An approximation:
    # unusual Markdown constructs may need manual review.
    slugs: set[str] = set(EXPLICIT.findall(text))
    seen: dict[str, int] = {}
    for heading in HEADING.findall(text):
        heading = re.sub(r"<[^>]*>", "", heading)
        heading = heading.replace("`", "").replace("*", "").replace("_", "")
        heading = heading.lower().strip()
        heading = re.sub(r"[^\w\-\s]", "", heading, flags=re.UNICODE)
        base = re.sub(r"\s+", "-", heading)
        nth = seen.get(base, 0)
        seen[base] = nth + 1
        slugs.add(base if nth == 0 else f"{base}-{nth}")
    return slugs


def audit() -> list[str]:
    problems = []
    markdown = sorted(ROOT.rglob("*.md"))
    # Ignore local artifacts and nonrepository checkouts.
    markdown = [p for p in markdown if ".git" not in p.parts and ".venv" not in p.parts]
    for source in markdown:
        text = source.read_text(encoding="utf-8")
        # Fenced code is not documentation linking; omit it from scanning.
        prose = re.sub(r"(?ms)^(```|~~~).*?^\1[^\n]*$", "", text)
        for match in LINK.finditer(prose):
            href = match.group(1).strip("<>")
            if href.startswith(("//", "mailto:", "data:")):
                continue
            parsed = urlsplit(href)
            if parsed.scheme:
                continue
            file_part = unquote(parsed.path)
            if file_part.startswith("/"):
                continue  # site-absolute links cannot resolve against repo root
            target = (source.parent / file_part).resolve() if file_part else source
            if not target.is_relative_to(ROOT):
                problems.append(f"{source.relative_to(ROOT)}: out-of-repo link {href}")
                continue
            if not target.is_file():
                problems.append(f"{source.relative_to(ROOT)}: missing file {href}")
                continue
            if parsed.fragment and target.suffix.lower() == ".md":
                anchors = anchor_slugs(target.read_text(encoding="utf-8"))
                anchor = unquote(parsed.fragment)
                if anchor not in anchors:
                    problems.append(f"{source.relative_to(ROOT)}: unmatched anchor {href}")
    return problems


if __name__ == "__main__":
    issues = audit()
    for issue in issues:
        print(issue, file=sys.stderr)
    if issues:
        print(f"{len(issues)} possible broken internal links", file=sys.stderr)
        sys.exit(1)
    print("Inline relative Markdown links and fragments passed heuristic audit.")
