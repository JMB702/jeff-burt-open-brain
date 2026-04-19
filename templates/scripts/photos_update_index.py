#!/usr/bin/env python3
"""
Regenerate Photos/photos-index.json from the live Apple Photos library.

Reads the local Photos.sqlite via the osxphotos library. Filters out Hidden
and Recently Deleted photos. Emits one JSON object per photo with metadata
but no pixel data — GPS, timestamps, albums, keywords, face-cluster persons,
original filename, dimensions.

The resulting index is gitignored (see .gitignore) — photo GPS and album
data is sensitive, same rule as Location History/archive/.

Usage:
  python3 scripts/photos_update_index.py
  python3 scripts/photos_update_index.py --verbose
  python3 scripts/photos_update_index.py --output some/other/path.json

Prerequisites:
  - pip3 install osxphotos
  - Full Disk Access granted to the terminal / Claude Code process in
    System Settings -> Privacy & Security -> Full Disk Access.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "Photos" / "photos-index.json"


def iso_local(dt: datetime) -> str:
    """Render a datetime as ISO 8601 in its local offset, falling back to UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().isoformat()


def album_titles(photo) -> list[str]:
    # osxphotos exposes album titles via `photo.albums` (list of str). Older
    # versions returned AlbumInfo objects — normalize to str either way.
    out: list[str] = []
    for a in getattr(photo, "albums", []) or []:
        if isinstance(a, str):
            out.append(a)
        else:
            title = getattr(a, "title", None) or str(a)
            out.append(title)
    return sorted(set(out))


def person_names(photo) -> list[str]:
    names: list[str] = []
    for p in getattr(photo, "persons", []) or []:
        if isinstance(p, str):
            names.append(p)
        else:
            names.append(getattr(p, "name", str(p)))
    # Drop the osxphotos placeholder for unidentified faces
    return sorted({n for n in names if n and n != "_UNKNOWN_"})


def place_name(photo) -> str | None:
    place = getattr(photo, "place", None)
    if not place:
        return None
    name = getattr(place, "name", None)
    if name:
        return str(name)
    # Fall back to country/city if `name` isn't populated
    parts = [
        getattr(place, "city", None),
        getattr(place, "state_province", None),
        getattr(place, "country", None),
    ]
    parts = [p for p in parts if p]
    return ", ".join(parts) if parts else None


SCORE_FIELDS = (
    "overall", "curation", "promotion", "failure",
    "highlight_visibility", "behavioral",
    "harmonious_color", "immersiveness", "interaction",
    "interesting_subject", "intrusive_object_presence",
    "lively_color", "low_light", "noise",
    "pleasant_camera_tilt", "pleasant_composition",
    "pleasant_lighting", "pleasant_pattern",
    "pleasant_perspective", "pleasant_post_processing",
    "pleasant_reflection", "pleasant_symmetry",
    "sharply_focused_subject", "tastefully_blurred",
    "well_chosen_subject", "well_framed_subject",
    "well_timed_shot",
)


def score_to_dict(score) -> dict:
    if score is None:
        return {}
    out = {}
    for field in SCORE_FIELDS:
        val = getattr(score, field, None)
        if val is None:
            out[field] = None
        else:
            try:
                out[field] = float(val)
            except (TypeError, ValueError):
                out[field] = None
    return out


def list_field(obj, name: str) -> list[str]:
    val = getattr(obj, name, None) or []
    if isinstance(val, str):
        return [val]
    return [str(v) for v in val if v]


def search_info_fields(photo) -> dict:
    si = getattr(photo, "search_info", None)
    if si is None:
        return {}
    camera = getattr(si, "camera", "") or ""
    return {
        "scene_labels": list_field(si, "labels"),
        "detected_text": list_field(si, "detected_text"),
        "bodies_of_water": list_field(si, "bodies_of_water"),
        "venues": list_field(si, "venues"),
        "venue_types": list_field(si, "venue_types"),
        "neighborhoods": list_field(si, "neighborhoods"),
        "camera": str(camera),
    }


def burst_fields(photo) -> dict:
    return {
        "is_burst": bool(getattr(photo, "burst", False)),
        "is_key_selected": bool(getattr(photo, "burst_selected", False)),
        "default_pick": bool(getattr(photo, "burst_default_pick", False)),
    }


def photo_to_record(photo) -> dict | None:
    date = getattr(photo, "date", None)
    if date is None:
        return None

    lat = getattr(photo, "latitude", None)
    lng = getattr(photo, "longitude", None)

    original_filename = getattr(photo, "original_filename", None) or getattr(photo, "filename", None) or ""
    ext = Path(original_filename).suffix.lower()

    record = {
        "uuid": photo.uuid,
        "taken_at": iso_local(date),
        "lat": float(lat) if lat is not None else None,
        "lng": float(lng) if lng is not None else None,
        "place_name": place_name(photo),
        "albums": album_titles(photo),
        "keywords": sorted(set(getattr(photo, "keywords", []) or [])),
        "persons": person_names(photo),
        "favorite": bool(getattr(photo, "favorite", False)),
        "screenshot": bool(getattr(photo, "screenshot", False)),
        "ismovie": bool(getattr(photo, "ismovie", False)),
        "live_photo": bool(getattr(photo, "live_photo", False)),
        "rating": int(getattr(photo, "rating", 0) or 0),
        "original_filename": original_filename,
        "ext": ext,
        "width": getattr(photo, "width", None),
        "height": getattr(photo, "height", None),
        "score": score_to_dict(getattr(photo, "score", None)),
        "burst": burst_fields(photo),
        **search_info_fields(photo),
    }
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output path (default: Photos/photos-index.json)")
    parser.add_argument("--verbose", action="store_true", help="Log progress to stderr")
    parser.add_argument("--library", type=Path, default=None, help="Path to a specific Photos library (defaults to system library)")
    args = parser.parse_args()

    try:
        import osxphotos  # type: ignore
    except ImportError:
        print(
            "error: osxphotos is not installed. Run `pip3 install osxphotos`.\n"
            "See Photos/README.md for the full setup, including Full Disk Access.",
            file=sys.stderr,
        )
        return 3

    try:
        db = osxphotos.PhotosDB(str(args.library)) if args.library else osxphotos.PhotosDB()
    except Exception as e:
        print(
            f"error: could not open Photos library ({e}).\n"
            "Most common cause: Full Disk Access is not granted to this terminal.\n"
            "Fix: System Settings -> Privacy & Security -> Full Disk Access.",
            file=sys.stderr,
        )
        return 4

    # osxphotos exposes hidden/intrash filters via both keyword args and attributes.
    # Using attributes keeps this robust across library versions.
    all_photos = db.photos(intrash=False)
    if args.verbose:
        print(f"loaded {len(all_photos)} photos (excluding trash)", file=sys.stderr)

    records: list[dict] = []
    skipped_hidden = 0
    skipped_no_date = 0
    for photo in all_photos:
        if getattr(photo, "hidden", False):
            skipped_hidden += 1
            continue
        record = photo_to_record(photo)
        if record is None:
            skipped_no_date += 1
            continue
        records.append(record)

    records.sort(key=lambda r: r["taken_at"])

    if args.verbose:
        print(
            f"kept {len(records)} (skipped {skipped_hidden} hidden, "
            f"{skipped_no_date} without date)",
            file=sys.stderr,
        )

    output = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "library_path": str(getattr(db, "library_path", "")),
        "photo_count": len(records),
        "filters": {
            "hidden": "excluded",
            "recently_deleted": "excluded",
        },
        "photos": records,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    if args.verbose:
        print(f"wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
