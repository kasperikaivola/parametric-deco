# CAD backend

Python 3.12.14, build123d 0.13.0; all resolved dependencies are pinned in
requirements.lock. See pyproject.toml for direct constraints. A historical pre-support-revision environment recorded Python 3.11.17 and a 44-test suite/CLI harness; this is not the current validation ledger. Python 3.11
is the CI target; other supported interpreter versions use the same pins.

A real OpenCascade solid is extruded from a Shapely polygon with explicit
interior wires. The smoke test exports STEP and reloads it, checks a
100 × 40 × 6 mm bounding box, volume and empty material inside a 6.5 mm
polygonal hole. Board bores use 32 polygon segments and deco support bores use 64; contours are nominal and never kerf-offset here.
SVG uses the same polygon rings, not hidden-line projection. Meshes triangulate and extrude the identical authoritative polygons using the pinned mapbox-earcut backend, cached across every scene/view. The independent OpenCascade solids remain the collision/STEP boundary. Focused tests check watertightness, solid volume, exact cap union/area including holes/concavities, bounds and outward side-wall normals.

Primary API reference consulted 2026-10-27:
https://build123d.readthedocs.io/en/latest/import_export.html
The current docs describe development APIs; implementation was exercised
against the pinned installed release rather than inferred from the page.

Setup note: a discarded environment had incompatible OCP generations after
concurrent package installs. A fresh isolated environment resolved the
consistent 0.13.0 stack. No CAD backend fallback was needed.

Physical extrusion uses measured stock thickness; nominal thickness is retained as a stock designation. At the default assumed 6 mm, the demonstrated geometry is unchanged.
