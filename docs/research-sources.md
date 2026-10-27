# Research references

Primary documentation consulted during discussion on 2026-10-27. Capabilities and licensing can change; verify target versions when implementing. Suitability judgments in the design are project recommendations, not vendor claims.

## Geometry and fabrication

- [OpenSCAD overview](https://openscad.org/about.html): script-based CAD and extrusion.
- [OpenSCAD command-line documentation](https://files.openscad.org/documentation/manual/Using_OpenSCAD_in_a_command_line_environment.html): parameter overrides and export workflow; this page documents an older version, so check the installed CLI.
- [CadQuery import/export](https://cadquery.readthedocs.io/en/latest/importexport.html): assembly and drawing exports.
- [build123d import/export](https://build123d.readthedocs.io/en/latest/import_export.html): layered SVG/DXF and units; latest documentation may describe development versions.
- [Blender Geometry Nodes](https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/): procedural geometry.
- [Blender modelling](https://www.blender.org/features/modeling/): scripting and UV tools.
- [Rhino/Grasshopper](https://www.rhino3d.com/6/new/grasshopper/): parametric ecosystem; historical feature overview.
- [FreeCAD features](https://www.freecad.org/features.php): another parametric/Python-capable CAD alternative.
- [LightBurn kerf guide](https://docs.lightburnsoftware.com/latest/Guides/Test-KerfOffset/): cut compensation, material variation, and fit.
- [WikiHouse manufacturing](https://www.wikihouse.cc/guides/manufacturing): plywood thickness variability and tolerance testing. Its structural dimensions and tolerances are not adopted for this artwork.

## Visuals and mapping

- [Arena Advanced Output](https://resolume.com/support/advanced-output): output/mapping and presets.
- [Arena input selection](https://www.resolume.com/support/en/input-selection): masks and polygon slices.
- [Arena output transformation](https://resolume.com/support/output-transformation): warping.
- [Resolume Spout/Syphon](https://resolume.com/support/syphonspout): live application-to-application output.
- [Wire introduction](https://www.resolume.com/support/en/wire-introduction): sources, effects, controls, FFT, and slice integration.
- [Wire ISF](https://resolume.com/support/en/isf): shader integration; version-specific limitations must be checked.
- [Wire compatibility](https://resolume.com/support/en/patch-compatibility): target version and compiled patches.
- [MadMapper features](https://madmapper.com/madmapper/features): shaders, mapping, and interchange.
- [MadMapper 3D calibration](https://docs.madmapper.com/madmapper/6/4.-surfaces/advanced-3d-and-scanning): model-based alignment.
- [TouchDesigner mapping](https://derivative.ca/UserGuide/Projection_Mapping): Kantan and CamSchnappr.
- [TouchDesigner licensing](https://derivative.ca/UserGuide/Licensing): resolution and commercial-use restrictions.
- [openFrameworks shaders](https://openframeworks.cc/documentation/gl/ofShader/): native shader-renderer candidate.

MadMapper and TouchDesigner were considered as alternatives; Arena compatibility remains required. No third-party source verifies the project's proposed closing-rail mechanism.
