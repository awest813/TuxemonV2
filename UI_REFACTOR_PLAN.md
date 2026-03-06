# UI Refactor Plan

## Target module layout
- `engine/ui/UIManager`
- `engine/ui/UIStateMachine`
- `engine/ui/UILayoutSystem`
- `engine/ui/UIThemeSystem`
- `engine/ui/widgets/{Button,Panel,List,Slider,Tooltip}`
- `engine/ui/screens/{MainMenu,PauseMenu,Inventory,Settings}`

## Incremental migration strategy
1. **Introduce adapter layer first**
   - Keep existing state-driven UI operational.
   - Route existing states through `UIManager` façade without changing gameplay behavior.
2. **Event-driven UI input routing**
   - Add `UIInputRouter` and `GameInputRouter` split under centralized `InputManager` integration.
3. **Dirty-UI invalidation**
   - Add per-screen dirty flags and only recompute/re-render changed UI surfaces.
4. **Layout caching**
   - Cache static layout constraints and invalidate only when viewport/theme/content changes.
5. **Virtualized list widgets**
   - For inventory/save/browser screens, render only visible rows.

## Key guardrails
- Never break existing state transitions and gameplay scripts.
- Migrate screen-by-screen behind feature toggles.
- Keep compatibility with existing input binding and controller behavior.

## Performance goals
- UI frame cost under 10% of frame budget (~<1.6ms at 60 FPS target for most scenes).
- Stable p95 frame time under 16.7ms in common gameplay loops.
- Reduced redraw pressure via invalidation + virtualization.
