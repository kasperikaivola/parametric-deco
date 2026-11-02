# Concealed LED Mounting Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for the single integrated task below. User explicitly requests one implementer and one final reviewer; no additional agents or intermediate reviews.

**Goal:** Optional concealed addressable-strip mounts and single-input wiring for every generator.

**Architecture:** Shared post-assembly lighting generation, adapted to actual placed surfaces, with configuration, manufacturing geometry, deterministic route metadata and export integration. Keep unlit geometry unchanged and inventory immutable.

**Tech Stack:** Existing Python, build123d, Shapely, trimesh, desktop editor and pytest.

**Spec:** docs/superpowers/specs/2026-11-01-concealed-led-design.md

## Global Constraints

- All four styles; default off; actual concealed mechanical strip retention.
- Preserve immutable manufactured inventory and unrelated work.
- One bottom input, serial data route and internal power distribution.
- Exactly one full review after implementation; fix findings without another review.
- Physical and Wire/Arena checks NOT RUN.

## Review Focus

- Nondefault strip dimensions must fit or fail with actionable errors.
- Saved inventory replay must not silently manufacture or change saved parts.
- Cut geometry, preview and routing must describe the same physical mounts.
- Emission must intersect plywood and be shielded from the front.
- All styles and small envelopes must avoid empty/misleading lighting output.

### Task 1: Complete lighting feature

**Files:** Extend src/parametric_deco/config.py, assembly.py, desktop_state.py,
export/manifest.py and relevant preview/export integration. Create focused shared
lighting module(s), tests/test_lighting.py, documentation and enabled examples.
Inspect actual interfaces before choosing new signatures and record them in docs.

- [ ] Read AGENTS.md, existing assembly/model/inventory/export and desktop workflows.
- [ ] Write focused failing tests for configuration, disabled compatibility,
  physical carrier/retention geometry, all-style placement/aim/concealment,
  deterministic serial route and bottom input, and inventory replay.
- [ ] Implement shared configuration, actual carriers and cable retention,
  validation and inventory behavior using existing part/assembly interfaces.
- [ ] Integrate exports, desktop controls, route/BOM instructions and examples.
- [ ] Run focused tests, all Python tests, Ruff, JS syntax and example builds;
  render and inspect front/oblique lighting evidence for all styles.
- [ ] Commit completed implementation and record exact verification/limitations.
