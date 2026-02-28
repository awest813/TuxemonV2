# Tuxemon Roadmap

## Features

### Implemented
- [x] Breeding/Egg Hatching System
- [x] Day/Night Cycle
- [x] Fishing
- [x] Weather System

### Planned
- [x] Advanced Breeding Mechanics
  - [x] Taste mutation inheritance is now applied to offspring
  - [x] Dual-parent move inheritance now applies one move candidate from each parent
  - [x] Inherited parental moves now fill open child move capacity before replacing existing moves
  - [x] Offspring IVs now inherit per-stat parent values with bounded mutation
- [x] Online Trading
  - [x] Added trade-offer TTL defaults, expiration cleanup, and player-centric pending-offer queries
  - [x] Added pending-offer inbox queries plus participant-authorized offer cancellation
  - [x] Session 1/3: Added receiver-authorized offer acceptance/rejection flow and rejection lifecycle event
  - [x] Session 2/3: Persisted pending trade offers and TTL defaults across save/load with expired-offer cleanup
  - [x] Session 3/3: Added legacy timestamp compatibility for trade history/offers to keep older save data loadable
- [x] Multiplayer Battles
  - [x] Session 1/4: Added multiplayer battle challenge lifecycle (propose/cancel/accept/reject), TTL expiry, and save/load support
  - [x] Session 2/4: Integrated multiplayer battle challenge logs into game save/load flow so pending challenges and defaults persist in SaveData
  - [x] Session 3/4: Added legacy challenge-log key compatibility and malformed-entry tolerance during multiplayer battle log loading
  - [x] Session 4/4: Added persisted multiplayer battle resolution history (accepted/rejected/cancelled/expired) with player queries and bounded history retention
