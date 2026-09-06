---
file: README.md
version: 1.0
author: Samuel Cao
created: 2026-09-06
last_updated: 2026-09-06
description: Interactive completion map for the San Francisco Bay Trail.
ai_update: Update last_updated and version. Append changelog at bottom.
---

# Bay Trail Progress

An interactive map of the San Francisco Bay Trail that records which sections
you have travelled and shows how much is left.

Open `index.html` in a browser. No build step, no server. Basemap tiles need an
internet connection; everything else works offline.

## Using it

Click a segment on the map, or a row in the segment list, then mark it
travelled. Travel mode is recorded per entry, and the date is optional, so a
walk you did years ago and cannot date still counts.

A segment can hold several entries. Walking it out and back, or again years
later, adds entries without counting the miles twice: coverage is what a
segment contributes, and it contributes once.

**Colour by** switches what the map encodes, and the legend swaps with it.
Completion is the default because the map exists to answer what is left.

**Skip** marks a section you do not intend to walk. MTC labels segments by
Caltrans bikeway class, which describes road engineering rather than scenery,
so an industrial bike lane and a pleasant sidewalk path look identical in the
data. Skipping is the manual correction: bulk-skip the on-street mileage, then
un-skip the parts worth walking. With skipped sections excluded, the headline
measures the trail you actually intend to walk.

**Facility types** filters by bikeway class, in both the map and the total.

## Your record

Entries autosave to this browser's local storage, which is scratch space.
The durable record is the JSON export, which belongs in git. Export writes a
dated, versioned file; import merges by entry id, so importing twice is safe.

## Regenerating the trail data

```
python3 scripts/build_data_v1.1.py <bay_trail.geojson>
```

Downloaded from the MTC open data portal as GeoJSON. The script filters to the
spine, normalizes to the internal schema, flattens MultiLineString geometry and
trims coordinates to about one metre. Pass `--include-spur` for spur trails.

All source-specific field handling lives in that one script. Switching to a
different upstream source means rewriting it and nothing else.

## Data

Trail geometry: Metropolitan Transportation Commission, San Francisco Bay Trail.
Provided for planning purposes only, as-is, with no warranty as to completeness,
currentness or accuracy. Basemap: CARTO and OpenStreetMap contributors.

Current snapshot: 591 spine segments, 457 of them built, 284.5 built miles out
of a 484-mile planned alignment.

## CHANGELOG

- v1.0 (2026-09-06): Initial release.
