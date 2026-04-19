#!/usr/bin/env python3
"""
Rank photo candidates for a date range using Apple's own ML signals.

Filters and ranks the photos-index.json records so Claude can pick a handful
worth looking at (with vision, or just reporting to Jeff) instead of
skimming hundreds.

Uses:
- Apple's ScoreInfo (curation, overall, failure) for aesthetic ranking
- search_info.labels for scene filtering
- search_info.detected_text for pre-OCR'd text search
- bodies_of_water / venues / neighborhoods / place_name for location filtering
- burst grouping to collapse burst sequences to one keeper
- Temporal + GPS clustering to collapse "5 near-identical snaps" to one
- Jeff's favorite flag as the strongest single boost

Usage:
  python3 scripts/photos_candidates.py 2026-03-22
  python3 scripts/photos_candidates.py 2026-03-22 --top 10
  python3 scripts/photos_candidates.py 2026-03-22 --labels "Sky,Water"
  python3 scripts/photos_candidates.py 2026-03-22 --person "Tom Crowley"
  python3 scripts/photos_candidates.py 2026-03-22 --text "whiteboard"
  python3 scripts/photos_candidates.py 2026-03-22 --location "Siesta Key"
  python3 scripts/photos_candidates.py 2026-03-22 --explain
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "Photos" / "photos-index.json"

# Cluster thresholds for temporal/spatial dedup
CLUSTER_WINDOW_SECONDS = 60
CLUSTER_RADIUS_METERS = 25


def parse_iso(raw: str) -> datetime:
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    from math import asin, cos, radians, sin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, [a[0], a[1], b[0], b[1]])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371000 * 2 * asin(sqrt(h))


def load_index() -> dict:
    if not INDEX_PATH.exists():
        print(
            "error: Photos/photos-index.json does not exist.\n"
            "Build it with: python3 scripts/photos_update_index.py",
            file=sys.stderr,
        )
        sys.exit(5)
    return json.loads(INDEX_PATH.read_text())


def normalize(s: str) -> str:
    # Fold smart quotes and whitespace so --person matching is forgiving
    return (
        s.replace("\u201c", '"').replace("\u201d", '"')
         .replace("\u2018", "'").replace("\u2019", "'")
         .lower().strip()
    )


def filter_by_date(photos: list[dict], start: date, end: date) -> list[dict]:
    out = []
    for p in photos:
        try:
            taken = parse_iso(p["taken_at"])
        except (KeyError, ValueError):
            continue
        d = taken.astimezone().date()
        if start <= d <= end:
            out.append(p)
    return out


def apply_filters(
    photos: list[dict],
    labels: list[str] | None,
    text: str | None,
    location: str | None,
    person: str | None,
    include_screenshots: bool,
) -> list[dict]:
    norm_labels = [normalize(l) for l in (labels or [])]
    norm_text = normalize(text) if text else None
    norm_location = normalize(location) if location else None
    norm_person = normalize(person) if person else None

    out = []
    for p in photos:
        if not include_screenshots and p.get("screenshot"):
            continue
        if norm_labels:
            photo_labels = {normalize(l) for l in p.get("scene_labels", [])}
            if not any(ql in photo_labels for ql in norm_labels):
                continue
        if norm_text is not None:
            hay = " ".join(p.get("detected_text", []))
            if norm_text not in normalize(hay):
                continue
        if norm_location is not None:
            candidates = (
                p.get("bodies_of_water", [])
                + p.get("venues", [])
                + p.get("neighborhoods", [])
                + ([p["place_name"]] if p.get("place_name") else [])
            )
            if not any(norm_location in normalize(c) for c in candidates):
                continue
        if norm_person is not None:
            if not any(norm_person in normalize(person_name) for person_name in p.get("persons", [])):
                continue
        out.append(p)
    return out


def collapse_bursts(photos: list[dict]) -> tuple[list[dict], int]:
    """Keep only one photo per burst. Returns (kept, num_bursts_collapsed)."""
    bursts: dict[str, list[dict]] = {}
    non_bursts: list[dict] = []
    for p in photos:
        burst = p.get("burst", {}) or {}
        if not burst.get("is_burst"):
            non_bursts.append(p)
            continue
        # Group by taken_at second (as proxy for burst id, since the index
        # doesn't carry the burst_uuid). Bursts are consecutive — same second
        # at the same GPS means same burst.
        key = p["taken_at"][:19] + f"_{round(p.get('lat') or 0, 4)}_{round(p.get('lng') or 0, 4)}"
        bursts.setdefault(key, []).append(p)

    kept_from_bursts = []
    for group in bursts.values():
        selected = next((g for g in group if (g.get("burst") or {}).get("is_key_selected")), None)
        if selected is None:
            selected = next((g for g in group if (g.get("burst") or {}).get("default_pick")), None)
        if selected is None:
            selected = max(group, key=lambda g: (g.get("score") or {}).get("overall") or 0)
        kept_from_bursts.append(selected)

    return non_bursts + kept_from_bursts, len(bursts)


def collapse_clusters(photos: list[dict]) -> tuple[list[dict], int]:
    """Collapse photos within CLUSTER_WINDOW_SECONDS and CLUSTER_RADIUS_METERS
    to one representative. Returns (kept, num_clusters_merged)."""
    sorted_photos = sorted(photos, key=lambda p: p["taken_at"])
    clusters: list[list[dict]] = []
    for p in sorted_photos:
        try:
            t = parse_iso(p["taken_at"])
        except ValueError:
            clusters.append([p])
            continue
        placed = False
        for cluster in clusters:
            last = cluster[-1]
            try:
                last_t = parse_iso(last["taken_at"])
            except ValueError:
                continue
            if abs((t - last_t).total_seconds()) > CLUSTER_WINDOW_SECONDS:
                continue
            if p.get("lat") is not None and last.get("lat") is not None:
                dist = haversine_m(
                    (p["lat"], p["lng"]),
                    (last["lat"], last["lng"]),
                )
                if dist > CLUSTER_RADIUS_METERS:
                    continue
            cluster.append(p)
            placed = True
            break
        if not placed:
            clusters.append([p])

    kept = []
    merged = 0
    for cluster in clusters:
        if len(cluster) == 1:
            kept.append(cluster[0])
            continue
        merged += 1
        # Pick representative: favorite > highest curation > first by time
        favorites = [c for c in cluster if c.get("favorite")]
        pool = favorites or cluster
        rep = max(pool, key=lambda c: (c.get("score") or {}).get("curation") or 0)
        kept.append(rep)
    return kept, merged


def score_photo(p: dict, matched_labels: int) -> tuple[float, dict]:
    s = p.get("score") or {}
    curation = s.get("curation") or 0
    overall = s.get("overall") or 0
    failure = s.get("failure") or 0
    favorite = 1.0 if p.get("favorite") else 0.0
    persons_boost = 0.1 * len(p.get("persons", []))
    label_boost = 0.2 * matched_labels

    rank = (
        favorite
        + 1.0 * curation
        + 0.5 * overall
        - 0.5 * failure
        + persons_boost
        + label_boost
    )
    reasoning = {
        "favorite": favorite,
        "curation": curation,
        "overall_x0.5": 0.5 * overall,
        "failure_x-0.5": -0.5 * failure,
        "persons": persons_boost,
        "label_match": label_boost,
    }
    return rank, reasoning


def format_time(iso_taken: str) -> str:
    return parse_iso(iso_taken).astimezone().strftime("%-I:%M %p")


def format_candidate_line(rank_num: int, c: dict) -> str:
    p = c["photo"]
    t = format_time(p["taken_at"])
    place = p.get("place_name") or "—"
    # Keep place short
    place = place.split(",")[0]
    tags = []
    if p.get("favorite"):
        tags.append("favorite")
    if p.get("persons"):
        tags.append("people: " + ", ".join(p["persons"]))
    cur = (p.get("score") or {}).get("curation")
    if cur is not None:
        tags.append(f"cur={cur:.2f}")
    tag_str = f" — {'; '.join(tags)}" if tags else ""
    return (
        f"  {rank_num}. [rank={c['rank']:.2f}]  "
        f"{p['uuid']}  {t}  {place}{tag_str}  [{p.get('original_filename','')}]"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("start_date", help="Date (YYYY-MM-DD) or start of range")
    parser.add_argument("end_date", nargs="?", help="End of range (YYYY-MM-DD), inclusive")
    parser.add_argument("--top", type=int, default=5, help="How many candidates to return (default 5)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--labels", default=None, help="Comma-separated scene labels; match if ANY is present")
    parser.add_argument("--text", default=None, help="Substring search in Apple's pre-OCR'd detected_text")
    parser.add_argument("--location", default=None,
                        help="Substring match against bodies_of_water / venues / neighborhoods / place_name")
    parser.add_argument("--person", default=None, help="Require a face-cluster person name (substring, smart-quote tolerant)")
    parser.add_argument("--no-dedupe", action="store_true", help="Skip burst + temporal/GPS dedup")
    parser.add_argument("--include-screenshots", action="store_true", help="Include screenshots (excluded by default)")
    parser.add_argument("--explain", action="store_true", help="Show per-candidate scoring breakdown")
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

    labels = [l.strip() for l in args.labels.split(",")] if args.labels else None

    index = load_index()
    all_photos = index.get("photos", [])

    date_filtered = filter_by_date(all_photos, start, end)
    pool_size = len(date_filtered)

    filtered = apply_filters(
        date_filtered,
        labels=labels,
        text=args.text,
        location=args.location,
        person=args.person,
        include_screenshots=args.include_screenshots,
    )
    after_filter = len(filtered)

    if args.no_dedupe:
        deduped = filtered
        bursts_collapsed = 0
        clusters_merged = 0
    else:
        after_bursts, bursts_collapsed = collapse_bursts(filtered)
        deduped, clusters_merged = collapse_clusters(after_bursts)

    # Rank
    norm_labels = [normalize(l) for l in (labels or [])]
    ranked = []
    for p in deduped:
        matched = 0
        if norm_labels:
            photo_labels = {normalize(l) for l in p.get("scene_labels", [])}
            matched = sum(1 for ql in norm_labels if ql in photo_labels)
        rank, reasoning = score_photo(p, matched)
        ranked.append({"rank": rank, "reasoning": reasoning, "photo": p})
    ranked.sort(key=lambda c: c["rank"], reverse=True)
    top = ranked[: args.top]

    if args.json:
        out = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "filters": {
                "labels": labels, "text": args.text, "location": args.location,
                "person": args.person, "include_screenshots": args.include_screenshots,
                "no_dedupe": args.no_dedupe,
            },
            "total_pool": pool_size,
            "after_filter": after_filter,
            "after_dedupe": len(deduped),
            "bursts_collapsed": bursts_collapsed,
            "clusters_merged": clusters_merged,
            "candidates": top,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    header = (
        f"{start.isoformat()}"
        + (f"–{end.isoformat()}" if end != start else "")
        + f" candidates (top {len(top)} of pool={pool_size}"
        + (f", after filter={after_filter}" if after_filter != pool_size else "")
        + (f", deduped to {len(deduped)} [bursts={bursts_collapsed}, clusters={clusters_merged}]"
           if not args.no_dedupe else "")
        + "):"
    )
    print(header)
    for i, c in enumerate(top, 1):
        print(format_candidate_line(i, c))
        if args.explain:
            parts = [f"{k}={v:+.3f}" for k, v in c["reasoning"].items() if v]
            if parts:
                print(f"     why: {' '.join(parts)}")
            labels_p = c["photo"].get("scene_labels") or []
            if labels_p:
                print(f"     labels: {', '.join(labels_p)}")
            text_p = c["photo"].get("detected_text") or []
            if text_p:
                snippet = "; ".join(text_p)[:120]
                print(f"     detected_text: {snippet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
