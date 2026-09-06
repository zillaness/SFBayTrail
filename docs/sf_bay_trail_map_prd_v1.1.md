---
file: sf_bay_trail_map_prd_v1.1.md
version: 1.1
author: Samuel Cao
created: 2026-09-06
last_updated: 2026-09-06
description: Product requirements for an interactive SF Bay Trail completion map that records which sections have been traveled and visualizes progress.
ai_update: Update last_updated and version. Rename file to match. Append changelog at bottom.
---

# SF Bay Trail Completion Map, PRD v1.1

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
  Confirmed 2026-09-06: dates are kept and optional. No chronological playback
  slider in v1, since sharing happens after the fact rather than live.
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

## 4. Data foundation, measured

A snapshot of the MTC Bay Trail layer was obtained and profiled on 2026-09-06.
Everything below is measured from that file, not estimated.

**Shape:** 683 features, EPSG:4326, 631 LineString and 52 MultiLineString. The
MultiLineString cases mean geometry handling cannot assume a single ring.

**Composition:**

| Split | Count | Miles |
|---|---|---|
| Spine, existing | 457 | 284.5 |
| Spine, proposed | 134 | 199.4 |
| Spine, total planned | 591 | 483.9 |
| Spur (out of scope for v1) | 92 | 76.8 |

The v1 denominator is therefore **284.5 miles** of existing spine. The full planned
spine is 483.9 miles, so the Bay Trail is roughly 59 percent built.

**Useful attributes:** `segment_nu` (unique across all 683 features, so it is a
sound primary key), `county`, `city`, `agency`, `status`, `type`, `miles`, `feet`,
`legend`, `surface`, `class`, `year_cmplt`, plus sea level rise flood fields.

`year_cmplt` is populated for 412 features, including 162 marked `pre-1989` and
discrete years running through 2025. This is a free basis for a "when was this
built" view and for reporting newly opened trail after a snapshot refresh.

**Segment length distribution, existing spine (n=457):**

| Statistic | Miles |
|---|---|
| min | 0.015 |
| p25 | 0.176 |
| median | 0.368 |
| mean | 0.622 |
| p75 | 0.756 |
| p90 | 1.448 |
| max | 6.057 |

80 percent of segments are under one mile, but the 91 segments longer than a mile
hold 57 percent of all existing spine mileage. Both halves of that sentence matter
and section 5 addresses each.

**Finding that changes the product:** 76 existing spine segments, totalling
**46.0 miles**, are classified `Bay Trail (on street)` rather than off street.
That is 16 percent of the existing spine, and it is sidewalk or bike lane beside a
road rather than shoreline path. By surface, 216.4 miles are paved and 67.9 miles
are natural.

For a project about hiking the shoreline, "I walked the Bay Trail" means something
different on those 46 miles. On street versus off street should be a visible
distinction, not a hidden attribute. Proposed: render on-street segments with a
distinct treatment in the completion view, and report the two figures separately.

## 5. Core architectural decision: segment input, span-shaped storage

**Approved 2026-09-06.**

Records are stored as spans along a segment, but v1 only ever writes whole-segment
spans and the interface only offers whole-segment marking.

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
  "snapshot": "mtc-2026-09",
  "created": "2026-09-06"
}
```

In v1, `start_m` is always 0 and `end_m` is always the full segment length.

Why this shape rather than a plain boolean:

- Whole-segment marking is roughly a third of the build cost of point-snapping
  input, so v1 ships sooner and the hard interaction work is deferred.
- Adding partial entry later becomes purely additive interface work. No data
  migration, and no rewrite of the coverage math, because the storage and the
  statistics were already span-based.
- The extra cost today is writing two numbers instead of one boolean.

**Resolved 2026-09-06 with measured data.** The median existing spine segment is
0.368 miles and 80 percent are under a mile. That is a reasonable atomic unit, so
point-snapping input should not be built. Whole-segment marking is the v1
interface and may well be sufficient permanently.

The long tail is still real: 91 segments exceed a mile and hold 57 percent of
existing mileage, with the longest at 6.06 miles. Marking those all or nothing
loses precision where it matters most.

The cheap answer, if that becomes annoying in use, is to subdivide long segments
in the data preparation step rather than to build a new interaction. Splitting
existing spine segments above one mile at one-mile intervals adds 129 pieces,
taking the checklist from 457 to 586, and delivers roughly one-mile granularity
everywhere with no new interface work. Deferred until real use shows whether it is
needed, and gated on the licensing question in section 11, since subdivision
produces a derivative work.

`segment_nu` is the stable primary key. Records reference it plus the snapshot
version, so a refreshed snapshot can be diffed rather than blindly trusted.

Coverage per segment is the union of its span intervals. An out-and-back covers a
stretch once and counts once. There is no distance metric that sums repeats.

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

Headline: **percent of existing Bay Trail spine covered.**

Secondary, shown smaller:

- Miles of trail covered, out of miles existing.
- Percent of the full planned alignment, including not-yet-built segments.
- Per-county completion, nine progress bars.

Repeated travel over the same stretch counts once. There is deliberately no
"total miles walked" statistic, since it would double-count out-and-backs and
answer a question this map is not for.

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

## 11. Licensing, unresolved and blocking publication

Two MTC documents point in different directions and the conflict is not yet
resolved.

**The dataset notice** is a warranty and liability disclaimer. It says the data is
for planning purposes, provided as is, with no warranty, and that decisions should
be validated with the relevant city or county. It states no restriction on reuse.

**The site Terms of Use (revised 2024-02-14)** grant only a "personal, limited,
non-exclusive license ... for your personal, individual, non-commercial, and
non-automated use only," and then explicitly restrict use. Absent prior written
authorization, a user "may not sell, rent, lease, re-distribute, re-publish,
re-transmit, display publicly, modify, create derivative works from, or otherwise
exploit the Site, or any of its content."

Read literally, that language reaches four things this project wants to do:

| Planned action | Clause implicated |
|---|---|
| Commit the GeoJSON to a public repository | re-distribute, re-publish |
| Serve the map from GitHub Pages | display publicly |
| Export share images containing the alignment | display publicly, derivative works |
| Subdivide long segments (section 5) | modify, create derivative works |

Private, personal use of the data is squarely inside what the terms grant. Every
publication step is what is in question.

There is genuine tension here worth noting rather than glossing: MTC operates the
material as an open data portal, whose purpose is reuse, and the dataset's own
notice imposes no reuse restriction. California also has relevant precedent on
public agencies attaching restrictive end-user terms to GIS records. None of that
is a determination, and this document does not offer legal advice. It records a
conflict that a person needs to decide on.

**Nothing has been published.** No MTC data has been committed to this repository.
The repository currently contains this document only.

**Options:**

| Option | Effect |
|---|---|
| **A. Request written authorization** | Email MTC and ask. The terms name written authorization as the route. Likely granted for a personal hobby project. Costs an email and a wait. |
| **B. Switch to OpenStreetMap** | ODbL explicitly permits redistribution, public display, and derivative works with attribution and share-alike. Removes the question. Costs the official segmentation, `segment_nu` identifiers, proposed-segment status, and `year_cmplt`. |
| **C. Keep everything private** | Unambiguously within the granted license. Costs the GitHub Page and the sharing goal, which were stated requirements. |
| **D. Fetch from MTC at runtime** | Not a fix. Still public display, and it adds automated access, which the terms separately restrict. Rejected. |

**Recommendation: C now, A in parallel, B as fallback.** Flip the repository
private today, which is free since it holds one document. Build against the MTC
snapshot for personal use, which is permitted. Send the authorization request. If
it is granted, publish. If it is refused or unanswered, swap the data layer to
OpenStreetMap, which is why section 12 isolates data ingest behind a normalizer.

## 12. Other constraints and risks

| Risk | Severity | Handling |
|---|---|---|
| Public repository holds a personal location history | Reviewed, accepted by user 2026-09-06 | `traversals.json` records where and when, is world-readable, and persists in git history after deletion. Superseded in practice if the repository goes private per section 11. |
| Data source may change (MTC to OSM) | Medium | All ingest normalizes to one internal schema. The application never reads source fields directly, so a source swap touches one script. |
| Segment identifiers change on snapshot refresh | Medium | `segment_nu` plus a snapshot version is stored on every record. Refresh is a reviewed diff, never an automatic overwrite. |
| Denominator grows as trail opens | Low, by design | Percentage can fall without user error. Share exports stamp the snapshot version so old images stay interpretable. |
| MultiLineString geometry (52 features) | Low | Geometry code must handle multi-part features rather than assuming one ring. |
| Undated backlog distorts the recency view | Low | `date_precision` field; undated renders in a distinct neutral rather than a guessed date. |

## 13. Build plan

**Phase 1, ingest and normalize.** Script reads the source file, filters to spine,
normalizes to the internal schema, emits `data/segments.json`. Source-specific
logic lives only here. Blocked on section 11 only for what gets committed, not for
building.

**Phase 2, map and marking.** Render segments, whole-segment marking, mode and
optional date capture, edit and delete, localStorage autosave, JSON import and
export.

**Phase 3, views and statistics.** Four view modes with swapping legends, headline
and secondary metrics, per-county bars, on-street versus off-street reporting, the
checklist sidebar.

**Phase 4, sharing.** Share-card canvas render and PNG download, square and 9:16.

**Phase 5, later.** GPX import, spur trails, long-segment subdivision, hosting.

## 14. Open questions

1. **Which licensing option, A, B, or C?** Blocks publication, not building.
2. Should on-street segments be excluded from the headline percentage, shown as a
   separate statistic, or merely styled differently? Proposed: styled differently
   and reported separately, included in the headline.

## CHANGELOG

- v1.0 (2026-09-06): Initial draft. Written after an eight-question requirements
  interview covering GPS history, deployment, storage, repo location, scope,
  completion definition, mobile use, and backlog size.
- v1.1 (2026-09-06): Profiled the real MTC snapshot and replaced estimates with
  measured figures. Resolved the span-versus-segment question in favour of
  whole-segment input with span-shaped storage. Dropped the miles-travelled
  statistic so out-and-backs count once. Surfaced the 46 miles of on-street spine
  as a product issue. Added the licensing conflict between the dataset notice and
  the site Terms of Use, which blocks publication pending a decision.
