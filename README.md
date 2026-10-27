# Parametric Deco

A parametric system for designing one intertwined plywood sculpture and generating corresponding projection geometry and visual data.

The artwork is assembled from reusable modules, but should read as a continuous composition rather than several separate decorations. Physical parts and projection surfaces must derive from the same design and assembly records.

## Current status

Design and research stage, documented from the discussion on 2026-10-27. No fabrication-ready joint, structural capacity, CAD implementation, or working Arena exporter is claimed.

Initial preset: approximately **1,000 × 1,000 × 200 mm**, independently adjustable. Laser-cut plywood with one nominal thickness parameter, initially **6 mm**. Natural wood, coloured finishes, and neon finishes are options; white is not the intended default.

Modules are removed from the backplate to rearrange their parts, then reattached. The target is slotted internal construction with no individual rib fasteners, secured by a closing member retained through the backplate attachment. This mechanism requires prototyping.

## Documentation

- [Requirements](docs/requirements.md): confirmed scope, parameters, and reuse behaviour.
- [Decisions](docs/decisions.md): accepted choices, proposals, and unresolved questions.
- [Mechanical design](docs/mechanical-design.md): interfaces, assembly concept, and fabrication.
- [Software architecture](docs/software-architecture.md): shared model, CAD options, Arena, and custom rendering.
- [Prototype validation](docs/prototype-validation.md): tests before production.
- [Roadmap](docs/roadmap.md): staged development and exit criteria.
- [Research sources](docs/research-sources.md): primary references and limitations.

Start with one complete arm and its backing connection. Validate the joint and projection workflow before multiplying it into a full sculpture.
