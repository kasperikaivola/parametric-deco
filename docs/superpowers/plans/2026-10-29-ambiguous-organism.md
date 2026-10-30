# Ambiguous organism implementation plan

> Implement inline with superpowers:executing-plans. Repository AGENTS.md requires
> one final whole-change review; no task reviewers.

**Goal:** Replace the literal helmet mask with intricate, ambiguous multi-cavity anatomy in PR #3.
**Architecture:** Reuse creature module/root clamps, introduce revised planar profiles
and cap-mounted transverse rib/key parts, and retain shared inventory/export/preview tools.
**Tech Stack:** Python, Shapely, build123d/OCP, trimesh, Pillow, existing canvas viewer.
**Spec:** ../specs/2026-10-29-ambiguous-organism-design.md

## Constraints and review focus

New cuts and versioned inventory, no old/new substitution. One measured thickness.
Keys need real through slots, cap bearing and free gaps, not decorative contacts.
Scale/curl extremes must keep roots, ribs, clearances and mounting valid.
Raised pose must move all rib/key instances with its complete module.
Six unequal cavities must stay open through backing and construction regions.
Front/oblique artistic assessment is separate from automated success.

## Tasks

- [x] Add profile assertions for six varied cavities, no nose ridge, connected contours
  and open appendage channels; observe RED. Revise `geometry/creature_profiles.py`
  and `scripts/creature_study.py`; generate and inspect coarse front/oblique views.
- [x] Add assembly tests for real transverse ribs/retaining keys, bearing/slot geometry,
  version rejection, scale/curl/stock edges and immutable complete-module reuse;
  observe RED. Update `geometry/creature.py`, `creature_assembly.py`, backplate family,
  validation/exports as needed. Keep truthful per-part interface metadata.
- [x] Add a reproducible more frontal oblique view using `export/views.py`; retain all
  old view outputs. Build both poses and visible-only atlases. Inspect actual images,
  revise major forms if still helmet-like or repetitive plate stacks.
- [x] Update README, design/assembly guidance, evidence and progress. Run focused and
  full pytest, full CLI harness, Ruff, JS viewer logic and HTTP/export smoke checks.
- [x] One final review covering revision; fix material findings and verify without
  re-review. Publish changed files to existing PR #3, update PR body; do not merge.

Completed verification and review: [revision ledger](../../implementation/organism-revision-progress.md).
