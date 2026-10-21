# image-date-sorter

Two small tools for organising photos by their EXIF capture date:

- [`sort_images_by_date.py`](#sort_images_by_datepy): sorts images into `year/month/` folders.
- [`fix_future_dates.py`](#fix_future_datespy): finds images whose EXIF date is in the future and sets it to a date you give.

If some images have a wrong date, run `fix_future_dates.py` first, then sort.

Both work on macOS, Linux and Windows. The examples use `./script.py`; on
Windows run `uv run sort_images_by_date.py ...` and `python fix_future_dates.py ...`.

## sort_images_by_date.py

Sorts images into `year/month/` folders based on their EXIF capture date.
Walks all subfolders of the given path; filenames are never changed.

```
photos/                      photos/
├── holiday/IMG_1.jpg        ├── 2021/
├── misc/b/IMG_2.jpg   →     │   └── 03/IMG_1.jpg
└── IMG_3.heic               └── 2023/
                                 ├── 07/IMG_3.heic
                                 └── 12/IMG_2.jpg
```

### Requirements

[uv](https://docs.astral.sh/uv/). Dependencies (`pillow`, `pillow-heif`) are
declared inline in the script and installed automatically on first run.

Without uv: `pip install pillow pillow-heif` and run it with `python3`.

### Usage

```bash
./sort_images_by_date.py ~/Pictures/unsorted --dry-run   # preview, changes nothing
./sort_images_by_date.py ~/Pictures/unsorted              # sort in place
./sort_images_by_date.py ~/Pictures/unsorted --dest ~/Pictures/sorted --copy
```

| Option         | Effect                                                    |
|----------------|-----------------------------------------------------------|
| `--dest PATH`  | Target root folder (default: the source folder)           |
| `--copy`       | Copy instead of move                                      |
| `--dry-run`    | Only print what would happen                              |
| `--exif-only`  | Leave images without EXIF date in place (no file-date fallback) |
| `--keep-empty` | Don't remove folders left empty after moving              |

### Behaviour

- **Formats:** `.jpg .jpeg .png .tif .tiff .heic .heif .webp`
- **Date source:** EXIF `DateTimeOriginal`, falling back to `DateTimeDigitized`, then `DateTime`.
- **No EXIF date:** the file is sorted by its creation date instead, or by its
  modification date if that is earlier (copying a file resets the creation date
  but usually keeps the modification date). Each such file is listed in the
  output. With `--exif-only` these files are left where they are.
- **Name conflicts:** if the target already has a file with the same name, the
  image is skipped and reported — nothing is overwritten or renamed.
- **Re-runs are safe:** files already in the right place are left alone.
- **Cleanup:** folders emptied by moving are removed (a leftover `.DS_Store` on
  macOS or `Thumbs.db` on Windows keeps a folder from counting as empty).
- **File date fallback on Linux:** Linux doesn't expose a file's creation date,
  so only the modification date is used there.

Always start with `--dry-run` and check the summary line at the end.

## fix_future_dates.py

Finds images whose EXIF date lies in the future (e.g. a camera with a wrongly
set clock) and sets it to a date you give. Only the metadata is changed, never
the image itself.

### Requirements

[exiftool](https://exiftool.org/) on the PATH. The script itself only needs
plain Python 3.9+, no pip packages.

| System  | Install exiftool                                                      |
|---------|-----------------------------------------------------------------------|
| macOS   | `brew install exiftool`                                               |
| Linux   | `sudo apt install libimage-exiftool-perl` (Debian/Ubuntu), `sudo dnf install perl-Image-ExifTool` (Fedora) |
| Windows | `winget install OliverBetz.ExifTool`, or `scoop install exiftool`     |

Filenames with umlauts and other non-ASCII characters work on all systems.

### Usage

```bash
./fix_future_dates.py ~/Pictures/trip                                   # list affected images
./fix_future_dates.py ~/Pictures/trip --set-date 2024-07-28 --dry-run   # preview the change
./fix_future_dates.py ~/Pictures/trip --set-date 2024-07-28             # apply it
./fix_future_dates.py ~/Pictures/trip --set-date "2024-07-28 14:30"     # exact date and time
```

| Option            | Effect                                                      |
|-------------------|-------------------------------------------------------------|
| `--set-date DATE` | Replace future dates with `YYYY-MM-DD` or `"YYYY-MM-DD HH:MM"` |
| `--dry-run`       | Only print what would change                                |
| `--no-backup`     | Don't keep exiftool's `<name>_original` backup copies       |

### Behaviour

- **What counts as wrong:** any of `DateTimeOriginal`, `CreateDate` or
  `ModifyDate` that is later than now. Only those tags are rewritten; tags with
  a plausible date stay as they are.
- **Date without time:** each image keeps its original time of day, so photos
  stay in the order they were taken. With a time, all images get exactly that.
- **One date for everything found:** all future-dated images below the path get
  the same date. Point the script at one trip or camera folder at a time.
- **Backups:** exiftool keeps the original as `IMG_1.jpg_original` next to the
  file. Delete those once you're happy, or use `--no-backup`.
- **File dates are kept:** the file's modification date stays unchanged.
