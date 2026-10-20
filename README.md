# image-date-sorter

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

## Requirements

[uv](https://docs.astral.sh/uv/). Dependencies (`pillow`, `pillow-heif`) are
declared inline in the script and installed automatically on first run.

Without uv: `pip install pillow pillow-heif` and run it with `python3`.

## Usage

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
| `--keep-empty` | Don't remove folders left empty after moving              |

## Behaviour

- **Formats:** `.jpg .jpeg .png .tif .tiff .heic .heif .webp`
- **Date source:** EXIF `DateTimeOriginal`, falling back to `DateTimeDigitized`, then `DateTime`.
- **No EXIF date:** the file is left where it is and listed in the output.
- **Name conflicts:** if the target already has a file with the same name, the
  image is skipped and reported — nothing is overwritten or renamed.
- **Re-runs are safe:** files already in the right place are left alone.
- **Cleanup:** folders emptied by moving are removed (a leftover `.DS_Store` on
  macOS keeps a folder from counting as empty).

Always start with `--dry-run` and check the summary line at the end.
