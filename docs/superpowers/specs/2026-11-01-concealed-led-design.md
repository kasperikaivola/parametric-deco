# Optional concealed addressable lighting

Implement the user's requested optional LED mounting feature for laminar,
layered-creature, radial-weave and rib-study. User authorizes implementation,
one implementation agent and one final review agent, then merge to master.

Use a shared, default-off lighting configuration, with configurable strip width,
thickness, LED pitch, clearances and electrical estimates as appropriate. Preserve
the unlit output and immutable manufactured inventory. All user controls must be
available in JSON and the existing desktop configuration workflow.

Approaches considered: perimeter-facing strips would expose emitters and mostly
light the audience; rear-facing strips alone would mainly illuminate the wall.
Chosen approach: concealed segmented carriers behind design elements, aimed
inward/sideways or rearward toward nearby plywood, with opaque front shielding.
Use reusable mechanical retention, not only adhesive. Integrate actual carriers,
retention features and cable anchors in manufacturable CAD and cut exports.

Distribute mounts throughout the artwork rather than only around the backplate.
Respect existing mounting, structural joints, envelope, symmetry and cutting-bed
constraints. Include real placement evidence: host piece, emission direction,
target and concealment/clearance checks. Reject unsupported geometry/settings
clearly rather than producing misleading manufacturing success.

Provide one bottom power/data/ground input with strain relief, internal jumpers,
an explicit ordered serial data route and strip segment lengths/LED counts. Power
may branch internally from this same input with injection as needed. Document
connector current sizing, controller/data input semantics and voltage selection;
a data input is not a firmware programming port. Supply external/controller
requirements without claiming electronics are manufactured by the generator.

Export lighting instructions, routing/connection manifest and BOM alongside CAD,
inventory, preview and cuts. Include enabled examples and front/oblique evidence
for all four styles. Physical fit, optical performance, electrical/thermal tests
and Wire/Arena checks remain NOT RUN unless actually performed.

Routine carrier dimensions and placement algorithm choices are delegated to the
implementer, who must document the chosen values and practical limitations.
