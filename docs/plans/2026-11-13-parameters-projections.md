# Reliable parameters and live projections

Goal: improve parameter editing and build robustness, configure projection content,
and animate it on real selected physical surfaces in the existing Python/Qt GUI.

Retain schema v2, immutable saved inventory and common backplate holes. Use existing
limit metadata for typed dropdowns, including bools and nullable small integer sets.
Projection settings never contribute to manufacturing identity. Share one GLSL effect
function between WebGL preview and ISF exports; animation updates uniforms without
rebuilding CAD, reloading the page or uploading geometry each frame. Atlas changes
repack from a validated saved assembly in a worker.

Implementation:
1. Reproduce coupled parameter failures; preserve cap-slot bearing when selecting
   real grid mounting bores on short six-limb creatures. Cover representative
   cross-style boundary combinations without weakening physical validation.
2. Typed parameter delegates and dedicated projection controls, retaining JSON.
3. Validated saved content settings: four effects, seven coordinate modes, motion,
   pulse/edge width, feathering, colors, brightness, resolution and face selection.
4. Physical face triangulation, atlas textures and GPU animation; play/pause and
   static fallback. Preserve state through rapid edits and immutable exports.
5. Focused/full tests, generated examples, lint and Qt framebuffer checks. One
   complete review; fix material findings, verify, push and open a PR to master.

Final review (one round):
- Fixed P1: optional projection atlas packing errors are reported separately and
  never invalidate otherwise valid CAD or cutting exports. Settings/error details
  remain exported, and changing atlas settings retries from the saved assembly.
- Fixed P2: ISF exports save effective atlas dimensions/mode after CLI overrides.
  Explicit surface selections are recorded in projection-selection.json.

Review focus: typed null/bool/numeric round trips; rapid edits and worker failures;
saved inventory; holes/orientation; stopped/hidden animation; preview/export parity.
Physical and Resolume host validation fields remain not_run.
