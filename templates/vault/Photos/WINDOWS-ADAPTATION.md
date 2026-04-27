Adapting Open Brain's photos integration for non-macOS platforms.

The photos feature ships with a macOS-only backend (`osxphotos` reading Apple Photos' local SQLite database). Every other script in the pipeline is platform-independent — they all consume `Photos/photos-index.json`. If you can produce that file on your platform, you get the rest of the pipeline for free.

## What's Mac-specific

Only two scripts need a new backend on Windows/Linux:

| Script | What it does | Mac dependency |
|---|---|---|
| `scripts/photos_update_index.py` | Walks the photo library, writes `Photos/photos-index.json`. | `osxphotos` + Apple Photos DB. |
| `scripts/photos_export.py` | Given a UUID, materializes a single photo to `tmp/photo-exports/` for vision. | `osxphotos.PhotosDB().photos(uuid=...)`. |

Everything else (`photos_query.py`, `photos_for_entity.py`, `photos_candidates.py`, both skills) reads the index and is platform-neutral.

## The contract — `Photos/photos-index.json` schema

Your backend must produce a JSON file with this shape. Fields in **bold** are required; the rest may be `null` or empty but the keys should exist so downstream scripts don't crash.

```json
{
  "generated_at": "2026-04-18T22:12:34-04:00",
  "library_path": "<path to your photo source>",
  "photo_count": 20292,
  "filters": {
    "hidden": "excluded",
    "recently_deleted": "excluded"
  },
  "photos": [
    {
      "uuid": "ABC123-...",                     // stable identifier you pick
      "taken_at": "2026-03-22T17:45:33-04:00",  // ISO 8601 local time
      "lat": 27.300505,                         // float or null
      "lng": -82.56543,                         // float or null
      "place_name": "Some Park, Some City, Some State",  // string or null
      "albums": ["Trip 2026"],
      "keywords": [],
      "persons": ["Person Name"],               // face-cluster names or []
      "favorite": true,
      "screenshot": false,
      "ismovie": false,
      "live_photo": false,
      "rating": 0,                              // 0–5 star
      "original_filename": "IMG_1554.JPG",
      "ext": ".jpg",
      "width": 6048,
      "height": 8064,

      // Phase 2 fields — nice-to-have; ranker degrades gracefully without them
      "score": {
        "overall": 0.60,
        "curation": 0.75,
        "promotion": 0.0,
        "failure": -0.001,
        // ...23 more aesthetic dimensions; all optional
      },
      "scene_labels": ["Outdoor", "Sky", "Water"],
      "detected_text": [],
      "bodies_of_water": ["Gulf of America"],
      "venues": [],
      "venue_types": [],
      "neighborhoods": ["Lido Key"],
      "camera": "Apple iPhone 17 Pro Max",
      "burst": {
        "is_burst": false,
        "is_key_selected": false,
        "default_pick": false
      }
    }
  ]
}
```

As long as you produce this shape, `photos_query.py`, `photos_for_entity.py`, and `photos_candidates.py` all work unchanged.

## Suggested backends

### Windows Photos app

- The Windows Photos app stores metadata in a local SQLite database. Exact path varies by version.
- Pillow + `exifread` can pull EXIF/GPS/timestamps from the original JPEG/HEIC files.
- No built-in equivalent to Apple's face-cluster `persons` or `score` — you can skip those fields or plug in open-source alternatives (CLIP for scenes, Tesseract for OCR, open-source face-recognition libraries for clustering).

### Google Photos Takeout

- Periodically export via Google Takeout. Each photo ships with a JSON sidecar that has timestamp, GPS, description, and album membership.
- Simple to parse; no live DB required.
- Downside: not live. You re-export when you want fresh data.

### OneDrive / iCloud Drive / local folder

- Walk a directory tree, use `exifread` or `Pillow.ExifTags` for each file.
- Gives you the essentials (timestamp, GPS, camera) with zero platform dependencies.
- Skip `score`, `scene_labels`, `detected_text`, `persons` — or plug in ML libraries if you want them.

## What degrades without the full schema

The ranker (`photos_candidates.py`) uses this weighted formula:
```
rank = (favorite ? 1.0 : 0)
     + 1.0 * score.curation
     + 0.5 * score.overall
     - 0.5 * score.failure
     + 0.1 * len(persons)
     + 0.2 * (matching --labels count)
```

If you don't populate `score`, all the `score.X` terms become zero and the ranker falls back to favorite + face-tag count + label match. Still useful — just less nuanced.

If you don't populate `scene_labels`, `--labels` filters return nothing. `--location` still works via `place_name`.

If you don't populate `detected_text`, `--text` filters return nothing. You lose pre-OCR search; text-in-photo queries have to fall back to vision.

If you don't populate `persons`, `--person` filters return nothing. You can still filter by album if that's how you organize people.

The pipeline is designed to tolerate missing optional fields — the index just becomes less powerful. Start minimal (uuid, taken_at, lat, lng, place_name, original_filename) and add more as you need it.

## Implementing `photos_export.py`

Simpler than the indexer — given a UUID, copy the photo's original bytes (or a preview) to `tmp/photo-exports/<uuid>.<ext>` and print the absolute path to stdout. That's the whole contract.

Your UUIDs can be anything stable — hash of the original file path, SHA of the file bytes, whatever — as long as the same photo always gets the same UUID and you can look up the bytes from it.

## Known `setup.sh` limitation

`Open brain set up/setup.sh` uses BSD `sed` (`sed -i ''`) which is macOS-only. On Linux, it will fail at block-stripping. If you're installing on Linux/Windows, use the AI-driven manual path in `SETUP-INSTRUCTIONS.md` — have an AI agent walk through the steps and do the substitutions itself.

## Contribute back

If you write a solid non-macOS backend, consider contributing it. The clean separation between "produce the index" and "use the index" means a Windows indexer slots in without touching any of the other scripts.
