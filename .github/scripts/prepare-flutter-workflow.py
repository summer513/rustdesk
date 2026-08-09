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


def main():
    text = WORKFLOW.read_text(encoding="utf-8")

    # 1. Insert patch step after every checkout step.
    marker = """      - name: Checkout source code
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
        with:
          submodules: recursive

"""
    text = text.replace(marker, marker + PATCH_STEP)

    # 2. Skip all jobs except the Windows-related ones.
    lines = text.splitlines(keepends=True)
    # Find the start of the jobs: section.
    jobs_start = None
    for idx, line in enumerate(lines):
        if line.strip() == "jobs:":
            jobs_start = idx
            break
    if jobs_start is None:
        raise RuntimeError("Could not find jobs: section")

    i = jobs_start + 1
    while i < len(lines):
        line = lines[i]
        # Job names are top-level keys under jobs, indented by 2 spaces, ending with colon.
        m = re.match(r"^  ([a-zA-Z0-9_-]+):\s*$", line)
        if m and i + 1 < len(lines):
            job_name = m.group(1)
            next_line = lines[i + 1]
            # Make sure next line is a job property (4-space indent), not a nested mapping key.
            if next_line.startswith("    ") and not next_line.startswith("      "):
                if job_name not in KEEP_JOBS:
                    # Insert if: false with 4-space indent right after job name line.
                    lines.insert(i + 1, "    if: false\n")
                    i += 1
        i += 1

    WORKFLOW.write_text("".join(lines), encoding="utf-8")
    print(f"Prepared {WORKFLOW}")


if __name__ == "__main__":
    main()
