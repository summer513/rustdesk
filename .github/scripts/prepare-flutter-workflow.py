#!/usr/bin/env python3
"""Modify flutter-build.yml for a focused Windows-only custom build."""
import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "flutter-build.yml"

PATCH_STEP = """      - name: Apply custom config patch
        shell: bash
        run: python3 .github/scripts/patch-rustdesk.py

"""

KEEP_JOBS = {
    "generate-bridge",
    "build-RustDeskTempTopMostWindow",
    "build-for-windows-flutter",
    "build-for-windows-sciter",
}


def find_job_blocks(lines):
    """Return list of (start_index, end_index, job_name) for top-level jobs."""
    jobs_start = None
    for idx, line in enumerate(lines):
        if line.strip() == "jobs:":
            jobs_start = idx
            break
    if jobs_start is None:
        raise RuntimeError("Could not find jobs: section")

    blocks = []
    i = jobs_start + 1
    while i < len(lines):
        m = re.match(r"^  ([a-zA-Z0-9_-]+):\s*$", lines[i])
        if m:
            job_name = m.group(1)
            start = i
            # Find end of this job block (next top-level job or end of file).
            j = i + 1
            while j < len(lines):
                if re.match(r"^  ([a-zA-Z0-9_-]+):\s*$", lines[j]):
                    break
                j += 1
            blocks.append((start, j, job_name))
            i = j
        else:
            i += 1
    return blocks


def main():
    text = WORKFLOW.read_text(encoding="utf-8")

    # 1. Insert patch step after every checkout step.
    marker = """      - name: Checkout source code
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
        with:
          submodules: recursive

"""
    text = text.replace(marker, marker + PATCH_STEP)

    lines = text.splitlines(keepends=True)
    blocks = find_job_blocks(lines)

    # Process skipped jobs from bottom to top so line indices remain valid.
    for start, end, job_name in reversed(blocks):
        if job_name in KEEP_JOBS:
            continue
        # Remove any existing top-level if: lines within this job block.
        new_block = [lines[start]]  # job name line
        new_block.append("    if: false\n")
        for k in range(start + 1, end):
            if re.match(r"^    if:\s*", lines[k]):
                continue
            new_block.append(lines[k])
        lines[start:end] = new_block

    WORKFLOW.write_text("".join(lines), encoding="utf-8")
    print(f"Prepared {WORKFLOW}")


if __name__ == "__main__":
    main()
