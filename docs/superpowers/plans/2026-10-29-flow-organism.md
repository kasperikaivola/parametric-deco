# Flow organism implementation plan

Goal: reusable alien ornament with independent composition, complexity and size.
Architecture: polar-field ribbons, independent relief plates and slotted trestles.
Tech: existing Python/build123d/Shapely CAD and export infrastructure.
Spec: ../specs/2026-10-29-flow-organism-design.md

Global constraints: 6 mm initial stock; immutable inventory; preserve legacy work;
physical/host validation NOT RUN; one whole-change review and no task reviewers.

Review focus: crowded secondary supports; minimum-size ligaments; hidden hardware
interference; inventory signature bypass; projection atlas/preview consistency.

- [x] Add strict `Organism` config and shared field/ribbon geometry. Write failing
  tests for separated controls, nested complexity and size validation, then implement.
  Generate coarse front/oblique studies and inspect before manufacturing joints.
- [x] Generate trestle joints/backing and assembly/inventory metadata. Tests cover
  dimensions, slot margins/necks, collisions/bearing, deterministic identity and
  rejected new cuts. Fix legacy neighboring-slot omission with regression.
- [x] Integrate existing export, projection and preview. Build low/medium/high,
  alternative composition and 800/1000/1400 sizes. Inspect actual CAD, record counts
  and limitations; run full suite and examples. One final whole-change review,
  fix material findings and verify fixes. Push to PR branch and rewrite PR body.

Pre-flight: config -> profiles -> assembly -> exporters share DesignConfig and
Assembly; add one family dispatch, leave old creature/radial contracts intact.

Execution: implemented inline; the single final whole-change review found legacy
signature compatibility, ineffective optimized-path test coverage, and repeated
hook anatomy. Fixed the legacy field set, verified the actual optimized path at
three rotations against OCP, and revised field-driven paths/unique relief levels.
The final verification and publication are recorded in the execution document.
