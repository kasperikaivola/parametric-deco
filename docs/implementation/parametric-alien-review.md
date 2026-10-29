# Final whole-revision review — configurable alien family

Reviewed `b0de3e8..7c824f9` once, read-only. The same independent reviewer resumed
after a usage/session interruption; no second review or per-task reviews were run.
All eight committed front/three-quarter images, config, profiles, generator,
assembly/inventory paths and exported artifacts were inspected.

## Findings

Critical: none. Important: none demonstrated. Two Minor findings are deferred.

1. **Neighboring rib slots are absent from the 7 mm margin guard.**
   `geometry/creature.py` checks a slot against the cap before any rib slots are
   subtracted. It enforces outline/channel/root-hole margins but not separation
   from the other rib slots. The main parameter documentation's claim of 7 mm
   around every slot is therefore incomplete.

   Exact generator reproduction:

   ```python
   DesignConfig(creature=CreatureMask(
       limb_count=6, ribs_per_limb=7,
       limb_reach=.85, limb_width=.9, scale=.9,
       asymmetry=.15, shell_layers=4,
       limb_layers=3, rib_height_mm=45,
   ))
   ```

   Other values are defaults. Generation succeeds. Independently measured
   feeler-left slot gaps include 4.432322 mm (5/6), 5.726874 mm (4/5) and
   6.200052 mm (2/3). However, this recipe also has substantial retaining-key
   interference. After review, the implementer ran the COMPLETE assembly for the
   exact recipe and confirmed `digital_valid=False`, with solid-interference
   errors. The fabrication exporter rejects invalid assemblies. No digitally
   accepted invalid build is demonstrated by this case; do not describe it as one.
   A future fix should enforce inter-slot separation explicitly and add a focused
   regression, without silently changing the requested geometry.

2. **Scale's documentation omits rib-height scaling.**
   The parameter table describes scale as XY-only; `creature_profiles.py` also
   multiplies actual transverse-rib height by scale. For example, scale .9 reduces
   rib heights 10% while rib_height_mm is unchanged. Stock, root positions and
   joinery sizes retain their physical dimensions. Future documentation should
   describe this coupling rather than silently change the existing behavior.

## Evidence and assessment

Counts affect actual modules, shell plates, ribs, keys, backing roots, connections
and removal metadata; no hidden fixed limb pair was found. Strict count types and
finite shape controls are checked. Inventory signatures include every manufacturing
control, and old v1/v2 inventories fail explicitly.

The reviewer independently reloaded all four supplied build artifacts: validation
flags true; atlas IDs exactly equal recommended IDs (22/22/10/29). Rest/raised
physical identity tuples and manufactured-definition fingerprints match. The two-,
four- and six-limb examples visibly represent different compositions. Default
limbs sweep sideways/down rather than forming the earlier upward horns. The broad
central shell remains mask-like, curled ends are patterned, and backing pads remain
visible; final artistic acceptance is not inferred from test counts.

The complete suite recorded before interruption passed153 tests with1 explicit
missing Wire/Arena/offscreen-host skip (678.25s). Production source remained at the
reviewed commit afterward. CLI verification was resumed separately after its process
was lost; its final result is recorded in the execution ledger.

Verdict: ready for USER review as a digital physical-test candidate, with the two
minor limits recorded. This is not fabrication, structural, runtime or merge approval.

## Declined judgments / implementer rulings

- Whether the bounded cavity palette, six module positions and odd-count asymmetry
  are the user's preferred vocabulary. They match the chosen implementation scope;
  more topology requires extending recipes and their geometry checks.
- Final artistic acceptance remains the user's judgment. Further visual changes
  may require another geometry iteration and new cuts.
- Physical fit/load/strength, clip selection/security, wear, root preload/anchors,
  detached handling, real tool access and continuous assembly/removal are NOT RUN.
  Prototype results may require new hardware, contours, clearances or assembly aids.
- Actual browser rendering, Wire/Arena compilation and projector performance are
  NOT RUN. Runtime or calibration tests may require viewer/resource/mapping changes.
