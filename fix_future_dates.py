#!/usr/bin/env python3
"""Find images whose EXIF date lies in the future and set it to a given date.

Walks every subfolder of the given path. Without --set-date it only lists the
affected images. With --set-date it rewrites the future-dated EXIF tags
(DateTimeOriginal, CreateDate, ModifyDate); tags with a plausible date are not
touched. Only the metadata changes, never the image data.

If --set-date is a date without a time, each image keeps its original time of
day, so photos stay in the order they were taken.

Requires exiftool on the PATH (works on macOS, Linux and Windows).

Usage:
    ./fix_future_dates.py ~/Pictures/trip                                   # list only
    ./fix_future_dates.py ~/Pictures/trip --set-date 2024-07-28 --dry-run
    ./fix_future_dates.py ~/Pictures/trip --set-date 2024-07-28
    ./fix_future_dates.py ~/Pictures/trip --set-date "2024-07-28 14:30"
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "tif", "tiff", "heic", "heif", "webp"]
DATE_TAGS = ["DateTimeOriginal", "CreateDate", "ModifyDate"]
EXIF_FORMAT = "%Y:%m:%d %H:%M:%S"


def parse_exif(raw: object) -> datetime | None:
    try:
        return datetime.strptime(str(raw).strip()[:19], EXIF_FORMAT)
    except ValueError:
        return None


def parse_set_date(value: str) -> tuple[datetime, bool]:
    """Return the parsed date and whether it included a time of day."""
    for fmt, has_time in (("%Y-%m-%d %H:%M:%S", True), ("%Y-%m-%d %H:%M", True), ("%Y-%m-%d", False)):
        try:
            return datetime.strptime(value, fmt), has_time
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"invalid date {value!r}, use YYYY-MM-DD or 'YYYY-MM-DD HH:MM'")


def run_exiftool(args: list[str]) -> subprocess.CompletedProcess:
    """Run exiftool with its arguments passed through a UTF-8 argfile.

    On Windows, exiftool can't handle non-ASCII filenames (e.g. umlauts) given on
    the command line. An argfile plus "-charset filename=utf8" works on every OS.
    The argfile is referenced by its bare name so its own path doesn't matter.
    """
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".args", delete=False) as f:
        f.write("\n".join(args) + "\n")
    try:
        return subprocess.run(
            ["exiftool", "-charset", "filename=utf8", "-@", os.path.basename(f.name)],
            cwd=os.path.dirname(f.name), capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    finally:
        os.unlink(f.name)


def read_dates(source: Path) -> list[dict]:
    """Read the EXIF date tags of all images below source in one exiftool call."""
    args = ["-json", "-r", "-q", "-q"]
    for ext in IMAGE_EXTENSIONS:
        args += ["-ext", ext]
    args += [f"-EXIF:{tag}" for tag in DATE_TAGS]
    args.append(str(source))
    out = run_exiftool(args).stdout
    return json.loads(out) if out.strip() else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="folder to scan recursively")
    parser.add_argument("--set-date", type=parse_set_date, metavar="DATE",
                        help="replace future dates with this date (YYYY-MM-DD or 'YYYY-MM-DD HH:MM')")
    parser.add_argument("--dry-run", action="store_true", help="only print what would change")
    parser.add_argument("--no-backup", action="store_true",
                        help="don't keep exiftool's <name>_original backup copies")
    args = parser.parse_args()

    if shutil.which("exiftool") is None:
        print("error: exiftool not found on PATH, see README for install steps", file=sys.stderr)
        return 1
    source = args.source.expanduser().resolve()
    if not source.is_dir():
        print(f"error: {source} is not a directory", file=sys.stderr)
        return 1

    now = datetime.now()
    if args.set_date and args.set_date[0] > now:
        print("error: --set-date is itself in the future", file=sys.stderr)
        return 1

    found = fixed = failed = 0
    for entry in sorted(read_dates(source), key=lambda e: e["SourceFile"]):
        future = {}
        for tag in DATE_TAGS:
            value = parse_exif(entry.get(tag, ""))
            if value and value > now:
                future[tag] = value
        if not future:
            continue

        found += 1
        path = entry["SourceFile"]
        listing = ", ".join(f"{tag} {value:%Y-%m-%d %H:%M}" for tag, value in future.items())
        if not args.set_date:
            print(f"{path}: {listing}")
            continue

        new_date, has_time = args.set_date
        updates = {}
        for tag, old in future.items():
            new = new_date if has_time else new_date.replace(hour=old.hour, minute=old.minute, second=old.second)
            updates[tag] = new
        changes = ", ".join(f"{tag} {future[tag]:%Y-%m-%d %H:%M} -> {new:%Y-%m-%d %H:%M}" for tag, new in updates.items())
        print(f"{path}: {changes}")
        if args.dry_run:
            continue

        # -P keeps the file's modification date, which the sorter uses as fallback.
        cmd = ["-q", "-P"]
        if args.no_backup:
            cmd.append("-overwrite_original")
        cmd += [f"-EXIF:{tag}={new.strftime(EXIF_FORMAT)}" for tag, new in updates.items()]
        cmd.append(path)
        result = run_exiftool(cmd)
        if result.returncode == 0:
            fixed += 1
        else:
            print(f"  failed: {result.stderr.strip()}", file=sys.stderr)
            failed += 1

    if not args.set_date:
        print(f"\n{found} image(s) with a future date. Fix them with --set-date YYYY-MM-DD.")
    elif args.dry_run:
        print(f"\n[dry run] would have fixed {found} image(s)")
    else:
        print(f"\nfixed {fixed}, failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
