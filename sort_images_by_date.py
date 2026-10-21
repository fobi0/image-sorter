#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow", "pillow-heif"]
# ///
"""Sort images into <dest>/<year>/<month>/<filename> using their EXIF capture date.

Walks every subfolder of the given path. Filenames are never changed: if the
target already contains a file with the same name, the image is skipped and
reported. Images without a usable EXIF date are sorted by the file's creation
date instead (or left in place with --exif-only).

Usage:
    ./sort_images_by_date.py ~/Pictures/unsorted --dry-run
    ./sort_images_by_date.py ~/Pictures/unsorted
    ./sort_images_by_date.py ~/Pictures/unsorted --dest ~/Pictures/sorted --copy
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".heif", ".webp"}

EXIF_IFD = 0x8769
TAG_DATETIME_ORIGINAL = 36867
TAG_DATETIME_DIGITIZED = 36868
TAG_DATETIME = 306


def exif_date(path: Path) -> datetime | None:
    """Return the capture date from EXIF, preferring DateTimeOriginal."""
    try:
        with Image.open(path) as img:
            exif = img.getexif()
    except Exception:
        return None

    sub = exif.get_ifd(EXIF_IFD)
    for raw in (
        sub.get(TAG_DATETIME_ORIGINAL),
        sub.get(TAG_DATETIME_DIGITIZED),
        exif.get(TAG_DATETIME),
    ):
        if not raw:
            continue
        try:
            return datetime.strptime(str(raw).strip("\x00 ")[:19], "%Y:%m:%d %H:%M:%S")
        except ValueError:
            continue
    return None


def file_date(path: Path) -> datetime:
    """Return the file's creation date, or its modification date if that is earlier.

    Copying a file resets its creation date but usually keeps the modification
    date, so the earlier of the two is the better guess for when it was taken.
    Creation date: st_birthtime on macOS (and Windows with Python 3.12+), st_ctime
    on older Windows Pythons. Linux doesn't expose it, so only mtime is used there.
    """
    st = path.stat()
    created = getattr(st, "st_birthtime", None)
    if created is None:
        created = st.st_ctime if sys.platform == "win32" else st.st_mtime
    return datetime.fromtimestamp(min(created, st.st_mtime))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="folder to scan recursively")
    parser.add_argument("--dest", type=Path, help="target root folder (default: same as source)")
    parser.add_argument("--copy", action="store_true", help="copy instead of move")
    parser.add_argument("--dry-run", action="store_true", help="only print what would happen")
    parser.add_argument("--exif-only", action="store_true", help="leave images without EXIF date in place")
    parser.add_argument("--keep-empty", action="store_true", help="don't remove folders emptied by the move")
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    dest = (args.dest or args.source).expanduser().resolve()
    if not source.is_dir():
        print(f"error: {source} is not a directory", file=sys.stderr)
        return 1

    # Collect the file list up front so files we move into dest aren't revisited.
    files = sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)

    planned: set[Path] = set()
    moved = skipped_no_date = used_file_date = skipped_conflict = already_sorted = 0
    for path in files:
        taken = exif_date(path)
        if taken is None:
            if args.exif_only:
                print(f"no EXIF date, left in place: {path}")
                skipped_no_date += 1
                continue
            taken = file_date(path)
            print(f"no EXIF date, using file date {taken:%Y-%m-%d}: {path}")
            used_file_date += 1

        target = dest / f"{taken.year:04d}" / f"{taken.month:02d}" / path.name
        if target == path:
            already_sorted += 1
            continue
        if target.exists() or target in planned:
            print(f"name conflict, skipped: {path} -> {target}")
            skipped_conflict += 1
            continue

        planned.add(target)
        print(f"{'copy' if args.copy else 'move'}: {path} -> {target}")
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            if args.copy:
                shutil.copy2(path, target)
            else:
                shutil.move(path, target)
        moved += 1

    if not args.copy and not args.dry_run and not args.keep_empty:
        # Deepest folders first so parents become empty after their children go.
        for folder in sorted((d for d in source.rglob("*") if d.is_dir()), key=lambda d: len(d.parts), reverse=True):
            try:
                folder.rmdir()  # only succeeds if empty
            except OSError:
                pass

    verb = "copied" if args.copy else "moved"
    prefix = "[dry run] would have " if args.dry_run else ""
    print(
        f"\n{prefix}{verb} {moved}, already sorted {already_sorted}, "
        f"sorted by file date {used_file_date}, no EXIF date (left in place) {skipped_no_date}, "
        f"name conflicts {skipped_conflict}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
