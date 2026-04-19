#!/usr/bin/env python3
"""
Find photos that match an Open Brain entity (event or project) by date,
and optionally by GPS radius if the caller supplies coordinates.

Reads the entity's YAML frontmatter to determine the date window:
  - Events: uses `date` (± --date-fuzz-days on each side).
  - Projects and Other Entities: uses `first_mention` and `last_entry_date`
    as the full window, padded by --date-fuzz-days.

Entity frontmatter does NOT carry lat/lng today — event `location` is a
free-text string like "Zoom" or "Tampa, FL". To filter by GPS, pass
--lat/--lng/--radius-km explicitly.

Usage:
  python3 scripts/photos_for_entity.py "events/AI Workgroup 2026-04-18.md"
  python3 scripts/photos_for_entity.py "projects/Jordan Paintings.md" --json
  python3 scripts/photos_for_entity.py "events/DEC Expo 2026.md" \\
      --lat 27.3364 --lng -82.5307 --radius-km 2.0
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "Photos" / "photos-index.json"


def parse_iso(raw: str) -> datetime:
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


def parse_frontmatter(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm: dict = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    from math import asin, cos, radians, sin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, [a[0], a[1], b[0], b[1]])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(h))


def derive_window(fm: dict, fuzz: int) -> tuple[date, date] | None:
    """Return (start, end) date window for the entity, or None if no dates."""
    event_date = fm.get("date")
    first = fm.get("first_mention")
    last = fm.get("last_entry_date")

    try:
        if event_date:
            d = date.fromisoformat(event_date)
            return d - timedelta(days=fuzz), d + timedelta(days=fuzz)
        if first and last:
            s = date.fromisoformat(first)
            e = date.fromisoformat(last)
            return s - timedelta(days=fuzz), e + timedelta(days=fuzz)
        if first:
            s = date.fromisoformat(first)
            return s - timedelta(days=fuzz), s + timedelta(days=fuzz)
        if last:
            e = date.fromisoformat(last)
            return e - timedelta(days=fuzz), e + timedelta(days=fuzz)
    except ValueError:
        return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("entity_file", type=Path, help="Path to an entity markdown file")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of formatted text")
    parser.add_argument("--date-fuzz-days", type=int, default=1, help="Pad the date window by this many days on each side (default: 1)")
    parser.add_argument("--lat", type=float, default=None, help="Optional GPS filter center latitude")
    parser.add_argument("--lng", type=float, default=None, help="Optional GPS filter center longitude")
    parser.add_argument("--radius-km", type=float, default=1.0, help="GPS filter radius in km (default: 1.0). Ignored without --lat/--lng.")
    args = parser.parse_args()

    entity_path = args.entity_file
    if not entity_path.is_absolute():
        entity_path = (ROOT / entity_path).resolve()

    if not entity_path.exists():
        print(f"error: entity file not found: {entity_path}", file=sys.stderr)
        return 2

    fm = parse_frontmatter(entity_path)
    if not fm:
        print(f"error: no YAML frontmatter in {entity_path}", file=sys.stderr)
        return 2

    window = derive_window(fm, args.date_fuzz_days)
    if window is None:
        print(
            f"error: entity has no usable date fields (date / first_mention / last_entry_date) in {entity_path}",
            file=sys.stderr,
        )
        return 2
    start, end = window

    if not INDEX_PATH.exists():
        print(
            "error: Photos/photos-index.json does not exist.\n"
            "Build it with: python3 scripts/photos_update_index.py",
            file=sys.stderr,
        )
        return 5

    index = json.loads(INDEX_PATH.read_text())
    photos = index.get("photos", [])

    use_gps = args.lat is not None and args.lng is not None
    center = (args.lat, args.lng) if use_gps else None

    matches: list[dict] = []
    for p in photos:
        try:
            taken = parse_iso(p["taken_at"])
        except (KeyError, ValueError):
            continue
        local_date = taken.astimezone().date()
        if not (start <= local_date <= end):
            continue
        distance_km = None
        if use_gps:
            lat, lng = p.get("lat"), p.get("lng")
            if lat is None or lng is None:
                continue
            distance_km = haversine_km(center, (lat, lng))
            if distance_km > args.radius_km:
                continue
        enriched = dict(p)
        if distance_km is not None:
            enriched["distance_km"] = round(distance_km, 3)
        matches.append(enriched)

    # Rank: closest first if GPS filter active, else by timestamp
    if use_gps:
        matches.sort(key=lambda m: (m.get("distance_km", 1e9), m["taken_at"]))
    else:
        matches.sort(key=lambda m: m["taken_at"])

    if args.json:
        out = {
            "entity": str(entity_path.relative_to(ROOT)) if entity_path.is_relative_to(ROOT) else str(entity_path),
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "gps_filter": (
                {"lat": args.lat, "lng": args.lng, "radius_km": args.radius_km}
                if use_gps else None
            ),
            "match_count": len(matches),
            "photos": matches,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    title = entity_path.stem
    print(f"{title}: {len(matches)} candidate photo(s) between {start} and {end}")
    if use_gps:
        print(f"  (within {args.radius_km} km of {args.lat}, {args.lng})")
    for m in matches:
        taken = parse_iso(m["taken_at"]).astimezone().strftime("%Y-%m-%d %-I:%M %p")
        lat, lng = m.get("lat"), m.get("lng")
        gps = f"({lat:.4f}, {lng:.4f})" if lat is not None and lng is not None else "(no GPS)"
        dist = f" — {m['distance_km']:.2f} km" if "distance_km" in m else ""
        place = m.get("place_name") or ""
        fname = m.get("original_filename", "")
        print(f"  {taken}  {m['uuid']}  {gps}{dist}  {place}  — {fname}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
