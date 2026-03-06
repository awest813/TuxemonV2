# Performance Report

## What was added
- Added runtime instrumentation (`RuntimeProfiler`) for:
  - Frame time
  - Update loop time
  - Render time
  - UI update time
  - UI render time
  - Input latency proxy
  - Asset loading time (map loading)
- Added F3 debug overlay showing live runtime metrics.

## Current measured signals (live, rolling window)
- Average frame time and p95 are computed from rolling samples.
- FPS is derived from average frame time.
- Memory uses `tracemalloc` current allocation.
- Draw calls are currently a **proxy** (`StateDrawer` drawn-state count).

## Profiling notes
- The project has no browser runtime, so `performance.mark()` / `measure()` are not applicable.
- Native external profilers (Tracy/Remotery/MicroProfile) are not integrated in this patch; the built-in profiler is now available in-engine.

## Initial optimization observations
1. `MapLoader.load_map_data()` performs sync disk + parse + merge work on cache misses; this now records `asset_load` timings.
2. Rendering pipeline is full-frame each draw interval; no global dirty-UI invalidation was previously present.
3. Input handling latency is now visible per frame as an input-stage duration proxy.

## Pending benchmark capture
To produce a strict before/after table with exact averages/p95 spikes and draw-call totals, run a representative gameplay scenario and capture F3 overlay telemetry for both baseline and optimized branches.
