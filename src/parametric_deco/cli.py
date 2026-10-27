"""Small local CLI; no remote services or laser operation."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys

from .config import load_config
from .model import Assembly, Inventory


def main(argv=None):
    parser = argparse.ArgumentParser(prog="parametric-deco")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "build", "reconfigure"):
        p = commands.add_parser(name)
        p.add_argument("config", type=Path)
        if name != "validate":
            p.add_argument("--out", type=Path, required=True)
            p.add_argument("--force", action="store_true")
        if name == "reconfigure":
            p.add_argument("--inventory", type=Path, required=True)
    p = commands.add_parser("preview")
    p.add_argument("directory", type=Path)
    p.add_argument("--port", type=int, default=8765)
    p = commands.add_parser("visuals")
    p.add_argument("directory", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--width", type=int, default=2048)
    p.add_argument("--height", type=int, default=2048)
    p.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "preview":
            directory = args.directory.resolve()
            if not (directory / "preview/index.html").is_file():
                raise ValueError("preview: directory must contain a generated preview/index.html")
            server = ThreadingHTTPServer(
                ("127.0.0.1", args.port),
                partial(SimpleHTTPRequestHandler, directory=str(directory)),
            )
            print(f"Preview: http://127.0.0.1:{server.server_port}/preview/", flush=True)
            try:
                server.serve_forever()
            finally:
                server.server_close()
            return 0
        if args.command == "visuals":
            from .visuals.atlas import generate_atlas
            from .visuals.isf import export_isf_resources

            assembly = Assembly.from_dict(
                json.loads((args.directory / "assembly.json").read_text())
            )
            atlas = generate_atlas(assembly, args.width, args.height)
            result = export_isf_resources(atlas, args.out, force=args.force)
            print(json.dumps({"files": len(result.paths), "out": str(args.out)}))
            return 0
        from .assembly import assemble

        config = load_config(args.config)
        inventory = Inventory.load(args.inventory) if args.command == "reconfigure" else None
        build = assemble(config, inventory)
        if args.command == "validate":
            print(json.dumps(build.report.to_dict(), indent=2))
            return 0 if build.report.digital_valid else 1
        from .export.manifest import export_build

        result = export_build(build, args.out, force=args.force)
        print(
            json.dumps(
                {"out": str(args.out), "files": len(result.paths), "warnings": result.warnings},
                indent=2,
            )
        )
        return 0
    except KeyboardInterrupt:
        return 130
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"parametric-deco: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
