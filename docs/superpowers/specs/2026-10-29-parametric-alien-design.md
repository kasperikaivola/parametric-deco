# Parametric alien family

User requests implementation of alien rather than horn/helmet silhouette and real
numeric composition parameters, default limb count four. Implement inline in PR #3.

`limb_count` counts ALL appendages, default4, supported integers2..6 including odd
counts. First two are lateral limbs, next two lower graspers, last two lower feelers.
No fixed extra limb pair is secretly added. Stable module names preserve semantic
identification. Counts choose coherent root/path recipes; shape controls vary them.

Expose cavity_count3..8(default6), ribs_per_limb3..7(default6), shell_layers3..6(default6),
limb_layers3..5(default4), limb_reach .85..1.05(default1), limb_width .9..1.1(default1),
rib_height_mm45..80(default65), asymmetry0.. .15(default.08), plus existing scale/curl.
Finite floats required; counts are strict integers, not booleans/fractional floats.
Parameters must affect actual contours, cuts, IDs/counts, backing/assembly/export,
not only viewer visibility. Ranges bound exploration; actual envelope, collisions,
slot margins and hardware still gate combinations. Explain rejection rather than
silently changing requested counts, resizing stock, clipping geometry or dropping ribs.

Use existing planar ribs/key/clip/root-clamp mechanism. Four default paths sweep
outwards and fold down/in, with blunt articulated ends and controlled side variation.
Do not simply add horns around a ring. New silhouette/CAD family v3 needs new cuts;
old v1/v2 inventory must fail explicitly. Rest/raised pose within an unchanged v3
manufacturing request reuses every part; count/shape/thickness changes require cuts.

Approaches: hard-coded new example would repeat the problem; unrestricted topology
would outgrow mounting/joinery scope. Choose bounded composition generator with
numeric controls and six available coherent module root/path recipes. Keep radial
example and existing geometry/surface/ISF/Wire/GLB/orbit pipeline unchanged in role.
Actual front/oblique views, counts and checks are required for multiple examples.
Physical fit/security/strength/handling/access and browser/Wire/Arena/projector
runtime stay NOT RUN. One final whole-revision review; no task reviewers.
