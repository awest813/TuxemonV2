# Architecture Map

## Engine Core
- Main loop is implemented by `LocalPygameClient.main()` with a fixed target FPS gate and update/draw split. `BaseClient.update_states()` owns network, input, events, systems, and state stack updates. 
- State lifecycle is managed in `StateManager` (`push/pop/replace`, event hooks, active state updates).

## Rendering System
- Rendering path is `LocalPygameClient.draw()` -> `Renderer.draw()` -> `StateDrawer.draw()`.
- `StateDrawer` walks active states and draws from bottom to top, with early stop when a non-transparent full-screen state is found.
- Map/world rendering is delegated through `MapRenderer` bound in `LocalPygameClient`.

## UI Layer
- UI is distributed across `tuxemon/ui/*` helpers and many state-specific screens in `tuxemon/states/*`.
- Menus/HUD are mostly state-owned, not centralized behind one UI manager.
- Drawing is currently frame-driven; no global dirty-UI invalidation gate exists.

## Input System
- `InputManager` owns queue handling and device setup.
- `PygameEventQueueHandler.process_events()` polls pygame events and routes to keyboard/gamepad/mouse handlers.
- Inputs are transformed to `PlayerInput` and then consumed by `EventManager` / active states.

## Game Logic
- Core game orchestration sits in `BaseClient`: event engine, map manager, NPC manager, collision, pathfinder, weather/environment, combat/session systems.
- `StateManager` updates all active states each frame.

## Asset Management
- Images are loaded synchronously via `graphics.load_image()` / `pygame.image.load()`.
- Map pipeline uses `MapLoader.load_map_data()` with LRU cache (`OrderedDict`) and disk load + yaml merge on misses.
- Core effects/conditions are initialized with `init_assets()`.

## Networking
- `NetworkManager` is initialized in `BaseClient` and updated each frame.

## Threading Model
- Runtime is mostly single-threaded for update/render.
- Optional CLI command processor runs in a daemon thread and dispatches commands to main thread queue.

## Architecture Problems Detected
1. **UI coupling to gameplay/state logic**
   - Many menus are state classes and update directly with gameplay concerns.
2. **Main-thread synchronous IO**
   - Image/map loading paths are synchronous and can create frame spikes on cache misses.
3. **Redraw model is mostly full-frame**
   - State drawing is frame-driven with no UI invalidation manager.
4. **No centralized UI routing layer**
   - Input is centralized at device layer but not split into UI-vs-game routers.
5. **Limited built-in runtime telemetry**
   - Prior to this patch, there was no always-available frame/update/render/UI/memory overlay.
