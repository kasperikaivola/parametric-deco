import subprocess
import sys


def test_cli_validate_errors_and_build_overwrite(tmp_path):
    def cli(*args):
        return subprocess.run(
            [sys.executable, "-m", "parametric_deco.cli", *map(str, args)],
            capture_output=True,
            text=True,
        )

    valid = cli("validate", "examples/single-module.json")
    assert valid.returncode == 0, valid.stderr
    assert "not_run" in valid.stdout
    bad = tmp_path / "bad.json"
    bad.write_text('{"grid":{"pitch_x_mm":0}}')
    invalid = cli("validate", bad)
    assert invalid.returncode != 0
    assert "grid.pitch_x_mm" in invalid.stderr
    out = tmp_path / "demo"
    built = cli("build", "examples/single-module.json", "--out", out)
    assert built.returncode == 0, built.stderr
    assert (out / "assembly.glb").exists()
    assert cli("build", "examples/single-module.json", "--out", out).returncode != 0
