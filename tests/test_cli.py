import subprocess, sys, json

def test_cli_city_not_found_exits_clean(tmp_path):
    out = tmp_path / "r.json"
    p = subprocess.run(
        [sys.executable, "-m", "pipeline.cli", "--woj", "mazowieckie",
         "--miasto", "Nieistniejewo123", "--rooms", "3", "--max-pages", "1",
         "--json", str(out)],
        cwd="/Users/szepix/olx", capture_output=True, text=True, timeout=120)
    assert p.returncode == 0
    with open(out) as f:
        data = json.load(f)
    assert data["error"] == "city_not_found"
