"""Exercise documented CLI workflows and the localhost preview HTTP boundary."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request


def main():
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="deco-examples-") as directory:
        root = Path(directory)
        (root / "examples").symlink_to(repo / "examples", target_is_directory=True)
        commands = [
            ["validate", "examples/single-module.json"],
            ["build", "examples/single-module.json", "--out", "build/single"],
            ["visuals", "build/single", "--out", "build/single-visuals"],
            ["visuals", "build/single", "--out", "build/fronts", "--surfaces", "broad"],
            ["visuals", "build/single", "--out", "build/edges", "--surfaces", "exterior"],
            ["visuals", "build/single", "--out", "build/selected", "--surface", "m1-rib-0--front"],
            ["build", "examples/intertwined.json", "--out", "build/intertwined"],
            [
                "reconfigure",
                "examples/reconfigured.json",
                "--inventory",
                "build/intertwined/inventory.json",
                "--out",
                "build/reconfigured",
            ],
            ["visuals", "build/reconfigured", "--out", "build/reconfigured-visuals"],
        ]
        commands.extend(
            [
                ["build", "examples/radial-weave.json", "--out", "build/radial-weave"],
                [
                    "reconfigure",
                    "examples/radial-weave-reconfigured.json",
                    "--inventory",
                    "build/radial-weave/inventory.json",
                    "--out",
                    "build/radial-weave-reconfigured",
                ],
                ["visuals", "build/radial-weave", "--out", "build/radial-weave-visuals"],
                [
                    "visuals",
                    "build/radial-weave-reconfigured",
                    "--out",
                    "build/radial-weave-reconfigured-visuals",
                ],
            ]
        )
        commands.extend(
            [
                ["build", "examples/creature-mask.json", "--out", "build/creature-mask"],
                [
                    "reconfigure",
                    "examples/creature-mask-raised.json",
                    "--inventory",
                    "build/creature-mask/inventory.json",
                    "--out",
                    "build/creature-mask-raised",
                ],
                [
                    "visuals",
                    "build/creature-mask",
                    "--out",
                    "build/creature-mask-visuals",
                    "--visible-only",
                ],
                [
                    "visuals",
                    "build/creature-mask-raised",
                    "--out",
                    "build/creature-mask-raised-visuals",
                    "--visible-only",
                ],
            ]
        )
        for args in commands:
            print("RUN: parametric-deco " + " ".join(args), flush=True)
            result = subprocess.run(
                [sys.executable, "-m", "parametric_deco.cli", *args],
                cwd=root,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                print(result.stdout + result.stderr)
                return result.returncode
            print("PASS", flush=True)
        server = subprocess.Popen(
            [sys.executable, "-m", "parametric_deco.cli", "preview", "build/single", "--port", "0"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        try:
            line = server.stdout.readline().strip()
            if not line.startswith("Preview: "):
                raise RuntimeError("preview did not start: " + line)
            url = line.removeprefix("Preview: ")
            with urllib.request.urlopen(url, timeout=10) as response:
                assert b"Assembly study" in response.read()
            with urllib.request.urlopen(url + "viewer.js", timeout=10) as response:
                assert b"scene.json" in response.read()
            with urllib.request.urlopen(url + "../scene.json", timeout=10) as response:
                assert json.load(response)["units"] == "mm"
            print("PASS: localhost preview HTTP, HTML, JS and millimetre scene", flush=True)
        finally:
            server.terminate()
            server.wait(timeout=10)
        subprocess.run(
            ["node", str(repo / "tests/test_preview.js"), str(root / "build/single/scene.json")],
            cwd=repo,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
