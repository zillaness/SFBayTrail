"""
file: build_data_v1.1.py
version: 1.1
author: Samuel Cao
created: 2026-09-06
last_updated: 2026-09-06
description: Normalizes the MTC San Francisco Bay Trail GeoJSON into the app's internal segment schema, emitting a browser-loadable JS payload plus a JSON copy.
ai_update: Update last_updated and version. Rename file to match. Append changelog at bottom.

Source-specific logic lives ONLY in this file. The application never reads MTC
field names directly, so swapping the upstream source (for example to
OpenStreetMap) means rewriting this script and nothing else.

Usage:
    python3 scripts/build_data_v1.1.py <source.geojson> [--include-spur]
"""

import json
import os
import sys
import argparse
from datetime import date

SCHEMA_VERSION = "1.1"
COORD_PRECISION = 5  # ~1 metre; the source carries far more than is useful

# MTC types segments by Caltrans bikeway class. This is a road-engineering
# classification describing the physical facility, not a judgement about
# scenery, so it is surfaced to the user rather than interpreted for them.
BIKEWAY_CLASS = {
    "1": "Class I shared-use path",
    "2": "Class II bike lane",
    "3": "Class III signed bike route",
    "4": "Class IV protected bikeway",
}


def norm(value):
    """MTC uses ' ' (a single space) as its null. Collapse to None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def rings(geometry):
    """Flatten LineString and MultiLineString into a list of coordinate rings."""
    if not geometry:
        return []
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "LineString":
        parts = [coords]
    elif kind == "MultiLineString":
        parts = coords
    else:
        return []
    out = []
    for part in parts:
        ring = [
            [round(float(pt[0]), COORD_PRECISION), round(float(pt[1]), COORD_PRECISION)]
            for pt in part
            if pt and len(pt) >= 2
        ]
        if len(ring) >= 2:
            out.append(ring)
    return out


def year_completed(raw):
    """year_cmplt holds real years, the literal 'pre-1989', or nothing."""
    text = norm(raw)
    if not text:
        return None, None
    if text.lower().startswith("pre"):
        return None, text
    try:
        year = int(float(text))
    except ValueError:
        return None, text
    # 2103 and similar are clearly data entry errors; keep the raw, drop the year.
    if not (1900 <= year <= date.today().year + 1):
        return None, text
    return year, text


def miles_of(props):
    for key in ("miles", "feet"):
        text = norm(props.get(key))
        if not text:
            continue
        try:
            value = float(text)
        except ValueError:
            continue
        return value if key == "miles" else value / 5280.0
    return 0.0


def label_for(props):
    city = norm(props.get("city"))
    county = norm(props.get("county"))
    if city and county and city != county:
        return f"{city}, {county} County"
    return city or (f"{county} County" if county else "Unnamed segment")


def convert(feature):
    props = feature.get("properties") or {}
    geom = rings(feature.get("geometry"))
    if not geom:
        return None
    year, year_raw = year_completed(props.get("year_cmplt"))
    legend = norm(props.get("legend")) or ""
    return {
        "id": str(props.get("segment_nu")),
        "label": label_for(props),
        "county": norm(props.get("county")),
        "city": norm(props.get("city")),
        "agency": norm(props.get("agency")),
        "status": (norm(props.get("status")) or "").lower(),   # existing | proposed
        "kind": (norm(props.get("type")) or "").lower(),        # spine | spur
        "onStreet": "on street" in legend.lower(),
        "surface": (norm(props.get("surface")) or "unknown").lower(),
        "facility": BIKEWAY_CLASS.get(str(norm(props.get("class")) or ""), None),
        "miles": round(miles_of(props), 4),
        "yearCompleted": year,
        "yearRaw": year_raw,
        "geometry": geom,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--include-spur", action="store_true",
                        help="Include spur trails. v1 scope is spine only.")
    parser.add_argument("--snapshot", default="mtc-2026-09")
    args = parser.parse_args()

    with open(args.source, encoding="utf-8") as handle:
        raw = json.load(handle)

    wanted = {"spine"} | ({"spur"} if args.include_spur else set())
    segments, skipped = [], 0
    for feature in raw.get("features", []):
        record = convert(feature)
        if record is None:
            skipped += 1
            continue
        if record["kind"] not in wanted:
            continue
        segments.append(record)

    segments.sort(key=lambda s: (s["county"] or "", s["city"] or "", s["id"]))

    ids = [s["id"] for s in segments]
    assert len(ids) == len(set(ids)), "segment ids are not unique; cannot key records on them"

    existing = [s for s in segments if s["status"] == "existing"]
    payload = {
        "_metadata": {
            "file": "segments.json",
            "schemaVersion": SCHEMA_VERSION,
            "author": "Samuel Cao",
            "created": "2026-09-06",
            "last_updated": date.today().isoformat(),
            "description": "Normalized SF Bay Trail segments for the completion map.",
            "source": "Metropolitan Transportation Commission, San Francisco Bay Trail",
            "sourceNote": ("Provided by MTC for planning purposes only, as-is, with no "
                           "warranty as to completeness, currentness, or accuracy."),
            "snapshot": args.snapshot,
            "ai_update": ("Regenerate with scripts/build_data_v1.0.py rather than editing. "
                          "Update last_updated and schemaVersion; append to _changelog."),
        },
        "_changelog": [
            {"version": SCHEMA_VERSION, "date": "2026-09-06",
             "note": "Initial normalization from the MTC snapshot."}
        ],
        "stats": {
            "segments": len(segments),
            "existingSegments": len(existing),
            "existingMiles": round(sum(s["miles"] for s in existing), 2),
            "plannedMiles": round(sum(s["miles"] for s in segments), 2),
            "existingOnStreetMiles": round(
                sum(s["miles"] for s in existing if s["onStreet"]), 2),
            "counties": sorted({s["county"] for s in existing if s["county"]}),
        },
        "segments": segments,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/segments.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
    # A bare .json cannot be fetched from a file:// page, so the app loads this.
    with open("data/segments.js", "w", encoding="utf-8") as handle:
        handle.write("window.BAY_TRAIL_DATA=")
        json.dump(payload, handle, separators=(",", ":"))
        handle.write(";")

    s = payload["stats"]
    print(f"segments written   : {s['segments']} ({s['existingSegments']} existing)")
    print(f"existing miles     : {s['existingMiles']}")
    print(f"planned miles      : {s['plannedMiles']}")
    print(f"on-street existing : {s['existingOnStreetMiles']} mi")
    print(f"counties           : {len(s['counties'])}")
    print(f"features skipped   : {skipped} (no usable geometry)")


if __name__ == "__main__":
    main()

# CHANGELOG
# v1.0 (2026-09-06): Initial release. Normalizes MTC Bay Trail GeoJSON to the
#   internal schema, flattens MultiLineString, reduces coordinate precision to
#   ~1 m, and emits both a JS payload for file:// use and a JSON copy.
# v1.1 (2026-09-06): Carry the Caltrans bikeway class through as a readable
#   `facility` label, so on-street versus off-street can be judged rather than
#   taken on faith.
