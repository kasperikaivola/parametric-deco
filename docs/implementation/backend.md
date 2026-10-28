# CAD backend

Python 3.12.14, build123d 0.13.0; all resolved dependencies are pinned in
requirements.lock. See pyproject.toml for direct constraints. Python 3.11.17 also passed the final 44-test suite and full CLI harness. Python 3.11
is the CI target; other supported interpreter versions use the same pins.

A real OpenCascade solid is extruded from a Shapely polygon with explicit
interior wires. The smoke test exports STEP and reloads it, checks a
100 × 40 × 6 mm bounding box, volume and empty material inside a 6.5 mm
polygonal hole. Circular holes use 256 segments (radial sag <0.00025 mm
at diameter 6.5 mm); contours are nominal and never kerf-offset here.
SVG uses the same polygon rings, not hidden-line projection. Meshes are
OpenCascade tessellations, not replacements for the solid checks.

Primary API reference consulted 2026-10-27:
https://build123d.readthedocs.io/en/latest/import_export.html
The current docs describe development APIs; implementation was exercised
against the pinned installed release rather than inferred from the page.

Setup note: a discarded environment had incompatible OCP generations after
concurrent package installs. A fresh isolated environment resolved the
consistent 0.13.0 stack. No CAD backend fallback was needed.

Physical extrusion uses measured stock thickness; nominal thickness is retained as a stock designation. At the default assumed 6 mm, the demonstrated geometry is unchanged.
