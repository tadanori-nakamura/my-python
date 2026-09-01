#!/usr/bin/env python3
"""Render Mermaid blocks using local `mmdc` (mermaid-cli).

This script extracts ```mermaid``` blocks from Markdown files and renders each
block to `docs/<md-stem>-<n>.svg` using the `mmdc` CLI. It's intended for CI
environments where Node and @mermaid-js/mermaid-cli are available.
"""
import re
import sys
import argparse
from pathlib import Path
import subprocess

MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*(.*?)```", re.S)


def extract_mermaid_blocks(text):
    return [m.group(1).strip() for m in MERMAID_BLOCK_RE.finditer(text)]


def ensure_docs(base: Path):
    d = base / 'docs'
    d.mkdir(parents=True, exist_ok=True)
    return d


def render_with_mmdc(mmd_text: str, out_path: Path, mmdc_cmd='mmdc'):
    # Write to a temporary .mmd file
    tmp = out_path.with_suffix('.mmd')
    tmp.write_text(mmd_text, encoding='utf-8')
    cmd = [mmdc_cmd, '-i', str(tmp), '-o', str(out_path)]
    try:
        subprocess.run(cmd, check=True)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument('files', nargs='*', default=['totp-security-flowchart.md', 'README.md'])
    args = p.parse_args()

    base = Path(__file__).resolve().parents[1]
    docs = ensure_docs(base)

    rendered = []
    for file in args.files:
        path = (base / file)
        if not path.exists():
            print(f"Skipping {file}: not found")
            continue
        text = path.read_text(encoding='utf-8')
        blocks = extract_mermaid_blocks(text)
        if not blocks:
            print(f"No mermaid blocks in {file}")
            continue
        for i, block in enumerate(blocks, start=1):
            stem = path.stem
            out_name = f"{stem}-{i}.svg" if len(blocks) > 1 else f"{stem}.svg"
            out_path = docs / out_name
            print(f"Rendering {file} block {i} -> {out_path}")
            render_with_mmdc(block, out_path)
            rendered.append((file, out_path.relative_to(base)))

    if not rendered:
        print('No diagrams rendered.')
        sys.exit(1)
    print('Rendered:')
    for s, r in rendered:
        print(f' - {s} -> {r}')


if __name__ == '__main__':
    main()
