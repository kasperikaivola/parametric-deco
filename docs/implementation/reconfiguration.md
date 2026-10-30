# Rib-study inventory placement

The full style workflow is in the [design guide](../design.md). This page describes
`parameters.placements` for the explicit mechanical study.

All four modules use the same spine and closure revisions. Reusable rib
profiles are shared across modules and repeated via identified instances.
reconfigured.json assigns physical instance IDs explicitly, permutes rib profiles
among manufactured stations, and exchanges rib-0 between m1 and m2. It preserves every instance ID and definition fingerprint while
changing transforms, visual phase attribution and atlas mapping. It makes
no new cuts or silently resized spines. examples/inventory.json is a compact
saved inventory of the first arrangement; this manufactured fixture is kept unchanged. Generate a separate inventory for new cuts.

Commands are in cli.md. The integrated test checks both states, all root-grid
matches, envelope and actual static solid intersections, identity preservation,
and sampled +Z extraction. In these examples each module can be extracted
independently on the checked translation path; choose m1, m2, m3, m4 as a
convenient numbering order. Always support with a tray and hand pressure
before loosening root bolts; do not infer detached self-retention.

The first attempted layout had overlapping root closures/end tongues. It
failed with 180 and 1,610 mm³ collision reports. Moving the vertical modules
to compatible even-row root positions removed those collisions; none were
suppressed as intended contacts. The tests verify the corrected arrangement.

Partial arrangements retain all unassigned instances in inventory.json. Their
last placement transforms are reference poses, not a claim that they remain
installed. The perpendicular rib interface supplies a canonical placement basis,
so unused ribs can be restored even after the module is moved or rotated.

## Explicit physical assignments

Each placement accepts `spine_instance_ids` (two IDs), `closure_instance_id` and
`rib_instance_ids` (one per station_indices entry). These refer to physical IDs
in inventory.json, independently of earlier module_id values or ID spelling.
Any ID such as stock-17 is valid; rib-N is not a required naming convention.
The order of rib_instance_ids matches station_indices. Explicit rib assignments
take precedence over rib_order; no part may be assigned twice. Assigning parts
requires reconfigure/Inventory, not generate-new mode.

The example uses these fields. For legacy configurations with no assignments,
parts are selected from the reference module by role and deterministic definition
order, with rib_order indexing that pool. This compatibility convenience is not
needed for explicit assignments and never parses physical ID suffixes. New module
names require complete explicit assignments. Local poses are reconstructed from
manufactured paired slots and closure geometry, not the previous world poses or
current generator thickness/spacing. A short rib is rejected if it cannot contact
the manufactured closure plane; loaded assemblies also check +1 mm withdrawal
against the actual closure solid. These are geometric checks, not load approval.
