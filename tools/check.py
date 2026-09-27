#!/usr/bin/env python3
"""Check the README and its plates before pushing.

    python3 tools/check.py

Exits 1 if the README points at a file that isn't there, an <img> has no alt text,
a plate isn't well-formed XML or reaches outside itself (GitHub renders README images
with no network), a plate is unused, or a file has a BOM or CRLF line endings.
"""
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    problems = []
    plates = sorted((ROOT / "assets").glob("*.svg"))

    for path in [ROOT / "README.md", *plates]:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            problems.append(f"{path.name}: starts with a BOM")
        if b"\r\n" in raw:
            problems.append(f"{path.name}: CRLF line endings")

    text = (ROOT / "README.md").read_text("utf-8")
    images = re.findall(r'(?:src|srcset)="([^"]+)"', text)
    links = re.findall(r'href="([^"]+)"', text) + re.findall(r"\]\(([^)]+)\)", text)
    for ref in images + links:
        if not ref.startswith(("http://", "https://", "#")) and not (ROOT / ref).is_file():
            problems.append(f"README points at a missing file: {ref}")
    for tag in re.findall(r"<img\b[^>]*>", text):
        if " alt=" not in tag:
            problems.append(f"<img> without alt text: {tag[:60]}")

    used = {pathlib.PurePosixPath(ref).name for ref in images}
    for svg in plates:
        body = svg.read_text("utf-8")
        if "<!DOCTYPE" in body or "<!ENTITY" in body:  # plates never need one; refuse before parsing
            problems.append(f"{svg.name}: has a DOCTYPE or ENTITY")
            continue
        try:
            ET.fromstring(body)
        except ET.ParseError as err:
            problems.append(f"{svg.name}: not well-formed ({err})")
        if re.search(r'(?:href|src)="(?:https?:)?//', body) or "@import" in body or "<script" in body:
            problems.append(f"{svg.name}: reaches outside itself")
        if svg.name not in used:
            problems.append(f"{svg.name}: not used by the README")

    for problem in problems:
        print("FAIL", problem)
    print(f"{'FAIL' if problems else 'ok'}: {len(images)} images, {len(links)} links, {len(plates)} plates checked")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
