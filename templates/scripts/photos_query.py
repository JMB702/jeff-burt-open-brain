#!/usr/bin/env python3
"""
Query {{USER_FIRST_NAME}}'s Apple Photos library for a given date or date range.

Reads from Photos/photos-index.json by default (fast, no osxphotos needed).
Use --live to bypass the cache and query osxphotos directly against the
live Photos library (requires Full Disk Access).

The index only covers photos not in the Hidden album and not in Recently
Deleted — see scripts/photos_update_index.py.

Usage:
  python3 scripts/photos_query.py 2026-04-18
  python3 scripts/photos_query.py 2026-04-01 2026-04-18
  python3 scripts/photos_query.py 2026-04-18 --json
  python3 scripts/photos_query.py 2026-04-18 --summary
  python3 scripts/photos_query.py 2026-04-18 --gps-only
  python3 scripts/photos_query.py 2026-04-18 --live
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "Photos" / "photos-index.json"
STALE_THRESHOLD_DAYS = 7


def parse_iso(raw: str) -> datetime:
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


def load_index() -> dict | None:
    if not INDEX_PATH.exists():
        return None
    return json.loads(INDEX_PATH.read_text())


def warn_if_stale(index: dict) -> None:
    generated = index.get("generated_at")
    if not generated:
        return
    try:
        gen_dt = parse_iso(generated)
    except ValueError:
        return
    age = datetime.now(timezone.utc) - gen_dt.astimezone(timezone.utc)
    if age > timedelta(days=STALE_THRESHOLD_DAYS):
        days = int(age.total_seconds() / 86400)
        print(
            f"warn: photos-index.json is {days} days old. "
            f"Rebuild with: python3 scripts/photos_update_index.py",
            file=sys.stderr,
        )


def load_live_photos() -> list[dict]:
    """Load photos directly from osxphotos, bypassing the cache."""
    try:
        import osxphotos  # type: ignore
    except ImportError:
        print("error: osxphotos is not installed. Run `pip3 install osxphotos`.", file=sys.stderr)
        sys.exit(3)
    # Reuse the record-builder from the indexer to keep shapes identical.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from photos_update_index import photo_to_record  # noqa: E402
    try:
        db = osxphotos.PhotosDB()
    except Exception as e:
        print(f"error: could not open Photos library ({e}).", file=sys.stderr)
        sys.exit(4)
    records = []
    for photo in db.photos(intrash=False):
        if getattr(photo, "hidden", False):
            continue
        rec = photo_to_record(photo)
        if rec is not None:
            records.append(rec)
    records.sort(key=lambda r: r["taken_at"])
    return records


def filter_by_date(photos: list[dict], start: date, end: date) -> list[dict]:
    out = []
    for p in photos:
        try:
            taken = parse_iso(p["taken_at"])
        except (KeyError, ValueError):
            continue
        local_date = taken.astimezone().date()
        if start <= local_date <= end:
            out.append(p)
    return out


def format_time(iso_taken: str) -> str:
    local = parse_iso(iso_taken).astimezone()
    return local.strftime("%-I:%M %p")


def format_photo_line(p: dict) -> str:
    t = format_time(p["taken_at"])
    uuid = p.get("uuid", "?")
    lat = p.get("lat")
    lng = p.get("lng")
    if lat is not None and lng is not None:
        place = p.get("place_name")
        gps = f"({lat:.4f}, {lng:.4f})"
        where = f"{place} {gps}" if place else gps
    else:
        where = "(no GPS)"
    tags: list[str] = []
    if p.get("favorite"):
        tags.append("favorite")
    if p.get("screenshot"):
        tags.append("screenshot")
    if p.get("ismovie"):
        tags.append("movie")
    if p.get("persons"):
        tags.append("people: " + ", ".join(p["persons"]))
    if p.get("albums"):
        tags.append("albums: " + ", ".join(p["albums"]))
    tag_str = f"  [{'; '.join(tags)}]" if tags else ""
    fname = p.get("original_filename", "")
    return f"  {t}  {uuid}  {where}{tag_str}  — {fname}"


def print_day(target: date, photos: list[dict]) -> None:
    if not photos:
        print(f"{target.isoformat()}: no photos")
        return
    print(f"{target.isoformat()}: {len(photos)} photo(s)")
    for p in photos:
        print(format_photo_line(p))


def print_summary_day(target: date, photos: list[dict]) -> None:
    if not photos:
        print(f"{target.isoformat()}: 0 photos")
        return
    places = sorted({p["place_name"] for p in photos if p.get("place_name")})
    place_str = ", ".join(places) if places else "no resolved places"
    print(f"{target.isoformat()}: {len(photos)} photos — {place_str}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("start_date", help="Date (YYYY-MM-DD) or start of range")
    parser.add_argument("end_date", nargs="?", help="End of range (YYYY-MM-DD), inclusive")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of formatted text")
    parser.add_argument("--summary", action="store_true", help="One-line summary per day (compact)")
    parser.add_argument("--gps-only", action="store_true", help="Only include photos with GPS coordinates")
    parser.add_argument("--live", action="store_true", help="Bypass the cache and query osxphotos directly")
    args = parser.parse_args()

    try:
        start = date.fromisoformat(args.start_date)
        end = date.fromisoformat(args.end_date) if args.end_date else start
    except ValueError as e:
        print(f"error: invalid date — {e}", file=sys.stderr)
        return 2

    if end < start:
        print("error: end_date is before start_date", file=sys.stderr)
        return 2

    if args.live:
        photos = load_live_photos()
    else:
        index = load_index()
        if index is None:
            print(
                "error: Photos/photos-index.json does not exist.\n"
                "Build it with: python3 scripts/photos_update_index.py\n"
                "Or use --live to query the library directly.",
                file=sys.stderr,
            )
            return 5
        warn_if_stale(index)
        photos = index.get("photos", [])

    filtered = filter_by_date(photos, start, end)
    if args.gps_only:
        filtered = [p for p in filtered if p.get("lat") is not None and p.get("lng") is not None]

    if args.json:
        out = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "source": "live" if args.live else "cache",
            "photos": filtered,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    current = start
    while current <= end:
        day_photos = [p for p in filtered if parse_iso(p["taken_at"]).astimezone().date() == current]
        if args.summary:
            print_summary_day(current, day_photos)
        else:
            print_day(current, day_photos)
        current += timedelta(days=1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
