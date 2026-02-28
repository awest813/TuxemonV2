# Tuxemon Roadmap

## Features

### Implemented
- [x] Breeding/Egg Hatching System
- [x] Day/Night Cycle
- [x] Fishing
- [x] Weather System

### Planned
- [ ] Advanced Breeding Mechanics
  - [x] Taste mutation inheritance is now applied to offspring
  - [x] Dual-parent move inheritance now applies one move candidate from each parent
  - [x] Inherited parental moves now fill open child move capacity before replacing existing moves
- [ ] Online Trading
  - [x] Added trade-offer TTL defaults, expiration cleanup, and player-centric pending-offer queries
  - [x] Added pending-offer inbox queries plus participant-authorized offer cancellation
  - [x] Session 1/3: Added receiver-authorized offer acceptance/rejection flow and rejection lifecycle event
  - [x] Session 2/3: Persisted pending trade offers and TTL defaults across save/load with expired-offer cleanup
- [ ] Multiplayer Battles
