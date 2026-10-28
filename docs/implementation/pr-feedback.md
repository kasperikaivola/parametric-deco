# Owner PR #1 feedback — 2026-10-28

Addresses https://github.com/kasperikaivola/parametric-deco/pull/1#issuecomment-6457323349.
This is an implementation response to the owner's findings, with regression
verification and no newly commissioned review round.

| Finding | Resolution | Regression evidence |
| --- | --- | --- |
| P1: ribs can escape below the closure | The perpendicular interface now requires actual rib/closure contact height and paired slot positions. Reconfiguration rejects 81 mm ribs against a 116 mm closure. Loaded assemblies test +1 mm withdrawal against the actual closure solid. | Short-rib transplant rejected; loaded assembly reports closure_retention |
| P2: atlas spends most resolution on tiny walls | Select surfaces before packing. Default: 28 broad faces; hole walls opt-in. Physical-size allocation with common pixels/mm and aspect preservation replaces equal-sized cells. API/CLI support broad, exterior, all or explicit face IDs. | Supplied 2048² study: every rib tile has a short dimension >=160 px and texel size <=0.8 mm; 16:1 physical area receives approximately 16:1 pixels; selected face uses the available width |
| P2: inventory depends on old module names and rib-N IDs | Explicit spine_instance_ids, closure_instance_id and rib_instance_ids resolve against the complete physical inventory. No physical ID suffix parsing. Local placement bases come from manufactured interfaces rather than old poses. | stock-N IDs work; compatible ribs exchange between modules with new module names; double assignment rejected |
| P2: example does not establish integrated artwork | Follow the owner's explicitly offered alternative: mark Task 8 / Stage 5 INCOMPLETE. Existing layout/images are mechanical study fixtures. README, roadmap, plan and execution ledger no longer claim integrated visual completion. | Documentation boundary; mechanical tests deliberately do not assert artistic success |

The full software suite passes: **49 passed / 1 explicit host-rendering skip**
(Python 3.12.14, 124.08 s). The complete CLI harness, including broad/exterior/
explicit atlas selection, cross-module inventory reconfiguration and localhost
preview, passes. Ruff, formatter and whitespace checks pass. Hosted Python 3.11
CI must pass before the authorized merge.

Full intertwined artwork, physical fit/load/handling, Wire/Arena runtime, actual
browser rasterization and exhaustive disassembly remain separate incomplete or
NOT RUN items. These software corrections do not convert them into approvals.
