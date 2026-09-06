---
file: sf_bay_trail_map_prd_v1.0.md
version: 1.0
author: Samuel Cao
created: 2026-09-06
last_updated: 2026-09-06
description: Product requirements for an interactive SF Bay Trail completion map that records which sections have been traveled and visualizes progress.
ai_update: Update last_updated and version. Rename file to match. Append changelog at bottom.
---

# SF Bay Trail Completion Map, PRD v1.0

Status: **DRAFT, awaiting sign-off.** Nothing gets built until this is approved.

## 1. Problem

The Bay Trail is a roughly 500-mile planned alignment around San Francisco Bay,
substantially but not continuously built. It cannot be thru-hiked. The realistic
way to travel it is in disconnected pieces over years.

There is currently no record of which pieces have been traveled. The record lives
in memory. That produces four failures:

1. No way to know what percentage is done.
2. No way to see where the remaining gaps are, so no way to decide where to go next.
3. No durable log. Hikes done years ago are already fading.
4. Nothing shareable. The progress is invisible to anyone else.

The current workflow being replaced is "remember it." There is no app, no
spreadsheet, and no GPS track history worth importing.

## 2. Success criteria

The project succeeds if all of the following are true:

- Logging a traveled section takes under 30 seconds, including partial sections.
- The map answers "what is left" at a glance, without reading a legend.
- Completion percentage is exact, not estimated, and correctly handles overlapping
  and out-and-back travel.
- A section walked in 2019 with no remembered date can still be logged and counted.
- The record survives a full rewrite of the application code.
- One click produces an image suitable for posting to social media.

## 3. Scope

**In scope for v1:**

- Bay Trail **spine** only.
- Manual logging of traveled sections, including partial sections.
- Travel mode tracked per entry (foot, bike, other).
- Optional dates with explicit precision, since most of the backlog is undated.
- Multiple color-coded view modes, each with its own legend.
- Static image export for sharing.
- Runs as a local HTML file opened from disk.

**Out of scope for v1, planned for later:**

- Spur trails (same MTC dataset, so this is a data filter change, not a rebuild).
- Adjacent networks such as the Bay Area Ridge Trail (different data sources).
- GPX import with map matching.
- Logging from a phone while in the field.
- GitHub Pages hosting.

**Explicitly not doing:**

- Any server, account system, or backend.
- Rebuilding trail geometry that MTC already publishes.

## 4. Data foundation

The Metropolitan Transportation Commission publishes the authoritative Bay Trail
alignment as a GIS line layer, covering existing and proposed segments, typed as
spine or spur, carrying segment ID, county, and length in miles. MTC also
publishes a human-readable segment names list.

Decision: **vendor a snapshot** of this data into the repo rather than fetching it
live. Reasons: the app must work as a local file with no network; a live fetch
means MTC republishing and renumbering segments silently breaks every stored
record; a snapshot is diffable and its provenance is visible in git history.

Refreshing the snapshot becomes a deliberate, reviewed operation with a migration
step, which is the correct posture when segment IDs are foreign keys into a
personal history.

## 5. Core architectural decision: linear referencing

**This is the decision that is hardest to reverse. It needs explicit approval.**

Each logged entry is a **traversal**, stored as a span along a segment:

```
{
  "id": "t_0001",
  "seg_id": "MTC-0142",
  "start_m": 0,
  "end_m": 1840,
  "mode": "foot",
  "date": null,
  "date_precision": "unknown",
  "notes": "",
  "created": "2026-09-06"
}
```

`start_m` and `end_m` are distances in meters measured along that segment's
geometry, not raw coordinates.

Why this and not a simple "segment done" boolean:

- Partial completion is representable, and on a 500-mile trail done in pieces,
  partial is the normal case rather than the exception.
- Overlapping entries resolve correctly. Coverage per segment is the union of all
  traversal intervals, so walking the same stretch twice does not count twice.
- It separates two genuinely different numbers: **trail covered** (union of spans)
  and **miles traveled** (sum of spans). An out-and-back doubles the second and
  not the first. Both are worth showing.
- Percentages are computed, never hand-maintained.

The cost is real: point clicks must be projected onto the line geometry, which is
more work than a boolean checkbox. It buys a data model that will not need
migrating in six months.

## 6. Input methods

**Primary: two-click span entry.** Click a start point, click an end point. Both
snap to the nearest point on the nearest trail line. The proposed span highlights
live as a preview. A panel then captures mode, optional date, and notes.

This is the only method that handles the partial case, so it is the foundation.
The other two methods reduce to it rather than competing with it.

**Shortcut: whole-segment entry.** With a segment selected, one button logs it
end to end. Internally this writes the same traversal record with the span set to
the full segment length.

**Derived view: the checklist.** A sidebar lists every segment with its coverage
percentage, sorted by county. Clicking zooms the map. It reads the same data. It
is a way to look at the record, not a second way to enter it.

**Edit and delete are required, not optional.** The backlog is undated and
recalled from memory, so early entries will be wrong and will need correcting.

**Later: GPX import.** Highest fidelity and zero clicking, but map matching a
noisy GPS track to trail geometry is the hardest engineering in the project.
Deferred deliberately, not forgotten. The traversal model above already accepts
imported spans without modification.

## 7. View modes and legends

One color channel, one meaning at a time, with the legend swapping to match the
active view. A single map trying to encode completion and date and mode
simultaneously communicates none of them.

| View | Color encodes | Legend |
|---|---|---|
| **Completion** (default) | covered, uncovered, not yet built | 3 states |
| **Travel mode** | on foot, by bike, both, uncovered | 4 states |
| **Recency** | gradient by most recent date, with undated in a distinct neutral | ramp plus undated |
| **County** | categorical by county, paired with 9 progress bars | 9 counties |

Completion is the default because "what is left" is the question the map exists to
answer. The not-yet-built state matters: proposed segments are not walkable, and
counting them against progress produces a number that is permanently low and
tells you nothing.

## 8. Metrics

Headline: **percent of existing Bay Trail spine covered.** This is the honest and
achievable number.

Secondary, shown smaller:

- Percent of the full planned alignment, including not-yet-built segments.
- Total miles traveled (sums repeats).
- Total miles of trail covered (does not sum repeats).
- Per-county completion, nine progress bars.

## 9. Share export

A dedicated share-card render, not a screenshot of the interface. Renders the
active view to a high-resolution canvas with title, headline stat, legend, and
date, then downloads as PNG. Two aspect ratios: square and 9:16 vertical.

## 10. Storage

Two layers, which is the pattern the local-file deployment wants:

- **localStorage**: the working buffer. Every edit autosaves. Zero friction, no
  save button, nothing lost by closing the tab.
- **JSON file in the repo**: the durable record. An export button writes
  `data/traversals.json`, which gets committed. Import on load reads it back.

localStorage alone is not acceptable for a multi-year record, since a cache clear
or a new device destroys it. The JSON file is the real record and localStorage is
scratch space in front of it.

## 11. Constraints and risks

| Risk | Severity | Handling |
|---|---|---|
| Build environment cannot reach MTC or ArcGIS domains (403 on CONNECT) | **Blocking for real data** | Build against stub geometry first, swap in real data when available. See Phase 0. |
| MTC data license may restrict redistributing a vendored copy | **Open, must resolve before publishing** | Verify terms before the repo is made public. If redistribution is restricted, ship a fetch script instead of the data. |
| Repo visibility versus personal location history | **Open, must resolve** | `traversals.json` is a record of where and when you were. In a public repo it is a published location history. Needs an explicit decision. |
| Segment IDs change when MTC republishes | Medium | Snapshot is pinned. Refresh is a deliberate migration, not an automatic update. |
| Undated backlog entries distort the recency view | Low | `date_precision` field, with undated rendered in a distinct neutral rather than guessed. |

## 12. Build plan

**Phase 0, unblock.** Hand-build a small stub GeoJSON of a few fake segments.
Prove the linear referencing math, snapping, coverage union, and percentage
computation against it. This removes the network blocker from the critical path
entirely and makes the hard logic testable.

**Phase 1, real data.** Ingest the MTC spine snapshot, normalize fields, filter to
spine, vendor into `data/`. Requires either domain allowlisting or a manual
download.

**Phase 2, input and storage.** Two-click span entry with snapping, the entry
panel, edit and delete, localStorage autosave, JSON import and export.

**Phase 3, views and stats.** The four view modes with swapping legends, headline
and secondary metrics, per-county bars, the checklist sidebar.

**Phase 4, sharing.** Share-card canvas render and PNG download in both aspect
ratios.

**Phase 5, later.** GPX import, spur trails, GitHub Pages, phone field logging.

Phases 0 and 2 carry the real risk. Phases 3 and 4 are largely presentation work
on top of a correct model.

## 13. Open questions

1. Should the repo be public or private? This gates the location-history question.
2. Does the MTC license permit redistributing a vendored copy of the data?
3. Are all four view modes wanted in v1, or should Recency and County wait?
4. Preferred wording for the headline stat, for example "38% of the Bay Trail" versus
   "190 of 500 miles."

## CHANGELOG

- v1.0 (2026-09-06): Initial draft. Written after an eight-question requirements
  interview covering GPS history, deployment, storage, repo location, scope,
  completion definition, mobile use, and backlog size.
