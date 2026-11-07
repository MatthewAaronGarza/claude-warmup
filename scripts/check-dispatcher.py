"""Run the setup wizard against fake GitHub, browser, and clipboard commands."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
bash = shutil.which("bash") or r"C:\Program Files\Git\bin\bash.exe"
mocks = r'''
curl() { printf '%s' "$CHECK_HTTP"; }
gh() {
  case "$*" in
    *"--json databaseId,event"*)
      [[ "$CHECK_RUN" == dispatch ]] && printf '11\n'
      ;;
    *) printf '10\n' ;;
  esac
}
sleep() { :; }
wslview() { :; }
clip.exe() { cat >/dev/null; }
source scripts/setup-dispatcher.sh
'''


def run(token="", saved=None, http="204", run_kind="dispatch"):
    with tempfile.TemporaryDirectory(prefix=".dispatcher-check-", dir=root) as directory:
        sandbox = Path(directory).resolve()
        assert sandbox.is_relative_to(root), "Temporary files must stay inside the project"
        (sandbox / "scripts").mkdir()
        shutil.copyfile(root / "scripts/setup-dispatcher.sh", sandbox / "scripts/setup-dispatcher.sh")
        env_file = sandbox / ".env"
        if saved is not None:
            env_file.write_text(saved, encoding="utf-8", newline="\n")
        result = subprocess.run(
            [bash, "-c", mocks], cwd=sandbox, input=("\n" + token + "\n" * 6).encode(),
            capture_output=True, timeout=15,
            env={**os.environ, "CHECK_HTTP": http, "CHECK_RUN": run_kind},
        )
        result.stdout = result.stdout.decode("utf-8")
        contents = env_file.read_text(encoding="utf-8") if env_file.exists() else None
        assert "github_pat_fake" not in result.stdout, "The token must stay out of wizard output"
        return result, contents


result, saved = run("github_pat_fake_new")
assert result.returncode == 0 and "can start the workflow" in result.stdout
assert saved == "GITHUB_DISPATCH_TOKEN=github_pat_fake_new\n"

existing = "OTHER=keep\nGITHUB_DISPATCH_TOKEN=github_pat_fake_old\n"
result, saved = run(saved=existing)
assert result.returncode == 0 and saved == existing
assert "Enter keeps current" in result.stdout

result, saved = run("github_pat_fake_new", saved=existing)
assert result.returncode == 0
assert saved == "OTHER=keep\nGITHUB_DISPATCH_TOKEN=github_pat_fake_new\n"

result, saved = run()
assert result.returncode == 1 and "No token entered" in result.stdout and saved is None

result, _ = run("github_pat_fake_new", http="403")
assert result.returncode == 1 and "HTTP 403 instead of 204" in result.stdout

result, _ = run("github_pat_fake_new", run_kind="schedule")
assert result.returncode == 0 and "still to do by hand" in result.stdout
assert "GitHub started run" not in result.stdout

print("Dispatcher checks passed: new, reused, replaced, missing, rejected, and unconfirmed token/run.")
