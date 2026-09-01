#!/usr/bin/env python3
"""Render Mermaid diagrams from Markdown files to SVG using Kroki.

Saves output under `docs/` and optionally inserts an image link into README.md
so GitHub will display the diagram.
"""
import re
import os
import sys
import argparse
from pathlib import Path

try:
    import requests
except Exception:
    print("Missing dependency 'requests'. Install with: python -m pip install -r requirements.txt")
    sys.exit(2)

KROKI_URL = "https://kroki.io/mermaid/svg"

MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*(.*?)```", re.S)


def extract_mermaid_blocks(text):
    return [m.group(1).strip() for m in MERMAID_BLOCK_RE.finditer(text)]


def write_flow_files(base: Path, src: str, blocks: list):
    """Write each mermaid block to flows/<src-stem>-<i>.md and return paths."""
    flows = []
    flows_dir = base / "flows"
    flows_dir.mkdir(exist_ok=True)
    stem = Path(src).stem
    for i, block in enumerate(blocks, start=1):
        name = f"{stem}-{i}.md" if len(blocks) > 1 else f"{stem}.md"
        path = flows_dir / name
        path.write_text("```mermaid\n" + block + "\n```\n", encoding="utf-8")
        flows.append(path.relative_to(base))
    return flows


def render_svg(mermaid_text):
    resp = requests.post(KROKI_URL, data=mermaid_text.encode("utf-8"), headers={"Content-Type": "text/plain"})
    resp.raise_for_status()
    return resp.content


def ensure_docs_dir(base_dir: Path):
    docs = base_dir / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    return docs


def insert_image_to_readme(readme_path: Path, image_rel_path: str):
    text = readme_path.read_text(encoding="utf-8")
    img_line = f"![TOTP Flowchart]({image_rel_path})\n\n"
    if img_line.strip() in text:
        return False
    # Insert at the top after an optional HTML comment
    if text.startswith("<!--"):
        # preserve initial comment block
        end = text.find("-->")
        if end != -1:
            end += 3
            new = text[:end] + "\n\n" + img_line + text[end:]
        else:
            new = img_line + text
    else:
        new = img_line + text
    readme_path.write_text(new, encoding="utf-8")
    return True


def main():
    p = argparse.ArgumentParser(description="Render Mermaid diagrams from Markdown to SVG for GitHub.")
    p.add_argument("files", nargs="*", default=["totp-security-flowchart.md", "README.md"], help="Markdown files to scan")
    args = p.parse_args()

    base = Path(__file__).resolve().parents[1]
    docs = ensure_docs_dir(base)

    rendered = []
    for file in args.files:
        path = (base / file)
        if not path.exists():
            print(f"Skipping {file}: not found")
            continue
        text = path.read_text(encoding="utf-8")
        blocks = extract_mermaid_blocks(text)
        if not blocks:
            print(f"No mermaid blocks found in {file}")
            continue

        # Write individual flow markdown files so each block can be referenced/checked in separately
        flow_files = write_flow_files(base, file, blocks)

        for i, block in enumerate(blocks, start=1):
            name = Path(file).stem
            out_name = f"{name}-{i}.svg" if len(blocks) > 1 else f"{name}.svg"
            out_path = docs / out_name
            print(f"Rendering {file} block {i} -> {out_path}")
            try:
                svg = render_svg(block)
            except Exception as e:
                print(f"Failed to render {file} block {i}: {e}")
                continue
            out_path.write_bytes(svg)
            rendered.append((file, out_path.relative_to(base), i))

    # Insert image links into README for every rendered diagram
    readme_path = base / "README.md"
    for src, rel, idx in rendered:
        # alt text: <source-stem> (block N)
        stem = Path(src).stem
        alt = f"{stem} (block {idx})"
        image_rel = str(rel).replace('\\\\', '/')
        img_line = f"![{alt}]({image_rel})\n\n"
        text = readme_path.read_text(encoding="utf-8")
        if img_line.strip() in text:
            continue
        # append images at top after initial comment if present
        if text.startswith("<!--"):
            end = text.find("-->")
            if end != -1:
                end += 3
                new = text[:end] + "\n\n" + img_line + text[end:]
            else:
                new = img_line + text
        else:
            new = img_line + text
        readme_path.write_text(new, encoding="utf-8")
        print(f"Inserted image link into README.md: {image_rel}")

    if not rendered:
        print("No diagrams rendered.")
        sys.exit(1)
    print("Rendered diagrams:")
    for s, r in rendered:
        print(f" - {s} -> {r}")


if __name__ == "__main__":
    main()
