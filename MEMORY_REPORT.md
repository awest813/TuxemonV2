# Memory Report

## Audit findings
- Per-frame loops are mostly update/draw driven; hot paths can still allocate transient Python objects (lists/strings/event containers).
- Image and map loading are synchronous and can spike temporary allocations when not cached.
- No global memory telemetry was previously exposed in runtime UI.

## Changes made
- Added `tracemalloc`-based live memory display to the F3 performance overlay.
- Added rolling metric framework to correlate memory and frame spikes during runtime.

## Likely optimization targets
1. Avoid repeated temporary object creation in tight per-frame loops.
2. Expand immutable/cache reuse in UI layout/text rendering paths.
3. Continue moving expensive map/asset work behind cache and preloading.

## Recommended next steps
- Add object pooling for frequently rebuilt UI structures (menu rows/list entries).
- Prebuild frequently used text surfaces where content is static.
- Add map/asset preload queues for known transition destinations.
