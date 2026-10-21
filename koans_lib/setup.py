"""Reproducible, project-local builds of the two upstream executables."""
from __future__ import annotations

import argparse
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

from .runner import CourseError, digest, inside, installed_tools, run_process, rho_result, presentation
from .workspace import initialize_exercises


ROOT = Path(__file__).resolve().parent.parent


def download(spec: dict, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / spec["archive"]
    if dest.is_file() and digest(dest) == spec["sha256"]:
        return dest
    partial = dest.with_suffix(dest.suffix + ".part")
    print(f"Downloading {spec['archive']}…", flush=True)
    for attempt in range(3):
        try:
            request = urllib.request.Request(spec["url"], headers={"User-Agent": "f1r3lang-koans-setup/1"})
            with urllib.request.urlopen(request, timeout=60) as source, partial.open("wb") as target:
                shutil.copyfileobj(source, target)
            if digest(partial) != spec["sha256"]:
                raise CourseError(f"Checksum mismatch for {spec['archive']}; nothing from this download was installed.")
            partial.replace(dest)
            return dest
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as exc:
            if attempt == 2:
                raise CourseError(f"Could not download {spec['archive']}: {exc}. Run ./setup to retry.") from exc
            time.sleep(attempt + 1)
        finally:
            partial.unlink(missing_ok=True)
    raise AssertionError("unreachable")


def unpack_tar(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    base = dest.resolve()
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            target = (base / member.name).resolve()
            if not target.is_relative_to(base) or member.isdev() or member.isfifo():
                raise CourseError(f"Unsafe archive member: {member.name}")
            if member.issym() or member.islnk():
                link = ((target.parent if member.issym() else base) / member.linkname).resolve()
                if not link.is_relative_to(base):
                    raise CourseError(f"Unsafe archive link: {member.name}")
            # Resolve each member immediately before extraction: a preceding
            # archive symlink can change what a later relative path means.
            tar.extract(member, base)


def source_tree(spec: dict, cache: Path) -> Path:
    archive = download(spec, cache / "downloads")
    parent = cache / "sources"
    dest = parent / spec["root"]
    marker = dest / ".koans-source-sha256"
    if marker.is_file() and marker.read_text() == spec["sha256"]:
        return dest
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="unpack-", dir=parent) as work:
        unpack_tar(archive, Path(work))
        extracted = Path(work) / spec["root"]
        if not extracted.is_dir():
            raise CourseError(f"Archive root missing: {spec['root']}")
        if dest.exists():
            shutil.rmtree(dest)
        extracted.rename(dest)
    marker.write_text(spec["sha256"])
    return dest


def command(args: list[str], cwd: Path, env: dict | None = None) -> None:
    subprocess.run(args, cwd=cwd, env=env, check=True)


def install_rust(lock: dict, cache: Path) -> Path:
    dest = cache / "rust"
    marker = dest / ".koans-components.json"
    fingerprint = json.dumps(lock["rust"], sort_keys=True)
    if marker.is_file() and marker.read_text() == fingerprint and (dest / "bin/rustc").is_file() and (dest / "bin/cargo").is_file():
        return dest
    for component in lock["rust"]["components"]:
        archive = download(component, cache / "downloads")
        with tempfile.TemporaryDirectory(prefix="rust-install-", dir=cache) as work:
            unpack_tar(archive, Path(work))
            installer = Path(work) / component["root"]
            command(["bash", str(installer / "install.sh"), "--prefix=" + str(dest), "--disable-ldconfig"], installer)
    marker.write_text(fingerprint)
    return dest


def install_protoc(lock: dict, cache: Path) -> Path:
    spec = lock["protoc"]
    archive = download(spec, cache / "downloads")
    dest = cache / "protoc"
    dest.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        for name in source.namelist():
            if not (dest / name).resolve().is_relative_to(dest.resolve()):
                raise CourseError(f"Unsafe protoc archive member: {name}")
        source.extractall(dest)
    (dest / "bin/protoc").chmod(0o755)
    return dest


def smoke(tools: dict[str, Path], root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="smoke-", dir=root / ".toolchain") as work:
        work = Path(work)
        source = work / "smoke.rho"
        source.write_text('new c, stdout(`rho:io:stdout`) in { c!(7) | for (@x <- c where x > 0) { stdout!(x) } }\n')
        result = run_process([str(tools["rho"]), "--quiet", "--data-dir", str(work / "data"), str(source)], work, 30)
        result = rho_result(result, {"mode": "ordered", "events": ["7"]})
        if not result.passed:
            raise CourseError(f"Interpreter smoke test failed:\n{result.stdout}\n{result.stderr}")
        source = work / "smoke.module"
        source.write_text('Module Smoke { Theory T() { Types { Value; } Terms { One . |- "one" : Value; } } theory T() }\n')
        result = run_process([str(tools["module"]), str(source)], work, 30)
        if not result.passed or presentation(result.stdout)["Types"] != ["Value"]:
            raise CourseError(f"Elaborator smoke test failed:\n{result.stdout}\n{result.stderr}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the pinned f1r3lang tools locally.")
    parser.add_argument("--jobs", type=int, default=2, help="Rust build parallelism (default: 2)")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    cache = ROOT / ".toolchain"
    cache.mkdir(exist_ok=True)
    try:
        # Concurrent setup processes must not share partially installed tools.
        import fcntl
        with (cache / "setup.lock").open("w") as setup_lock:
            fcntl.flock(setup_lock, fcntl.LOCK_EX)
            try:
                tools = installed_tools(ROOT)
            except CourseError:
                tools = None
            if tools:
                smoke(tools, ROOT)
                initialize_exercises(ROOT)
                print("Setup is already complete. Run ./koans.")
                return 0
            lock = json.loads((ROOT / "toolchain.lock.json").read_text())
            if not isinstance(lock, dict) or lock.get("version") != 1:
                raise CourseError("Unsupported toolchain lock version.")
            print("Preparing the pinned tools. The first native build can take several minutes.\nBuilds are cached; rerunning setup preserves all exercise edits.", flush=True)
            rust = install_rust(lock, cache)
            protoc = install_protoc(lock, cache)
            runtime = source_tree(lock["runtime"], cache)
            elaborator = source_tree(lock["elaborator"], cache) / lock["elaborator"]["crate"]
            env = os.environ.copy()
            env.update(PATH=str(rust / "bin") + os.pathsep + env.get("PATH", ""),
                       RUSTC=str(rust / "bin/rustc"), RUSTDOC=str(rust / "bin/rustdoc"),
                       CARGO_HOME=str(cache / "cargo"), PROTOC=str(protoc / "bin/protoc"),
                       PROTOC_INCLUDE=str(protoc / "include"))
            cargo = str(rust / "bin/cargo")
            for name, directory in (("runtime", runtime), ("elaborator", elaborator)):
                pinned_lock = inside(ROOT, lock[name]["cargo_lock"])
                if digest(pinned_lock) != lock[name]["cargo_lock_sha256"]:
                    raise CourseError(f"The committed {name} Cargo.lock checksum does not match toolchain.lock.json.")
                shutil.copyfile(pinned_lock, directory / "Cargo.lock")
            print("Building the reference elaborator…", flush=True)
            command([cargo, "build", "--release", "--locked", "-j", str(args.jobs)], elaborator, env)
            print("Building the standalone interpreter…", flush=True)
            command([cargo, "build", "--release", "--locked", "--bin", "rholang-cli", "-j", str(args.jobs)], runtime, env)
            binaries = cache / "bin"
            binaries.mkdir(exist_ok=True)
            for name, built in (("mettail-elab", elaborator / "target/release/mettail-elab"),
                                ("rholang-cli", runtime / "target/release/rholang-cli")):
                staged = binaries / (name + ".part")
                shutil.copy2(built, staged)
                staged.chmod(0o755)
                staged.replace(binaries / name)
            tools = {"rho": binaries / "rholang-cli", "module": binaries / "mettail-elab"}
            smoke(tools, ROOT)
            receipt = {"lock_sha256": digest(ROOT / "toolchain.lock.json"),
                       "binaries": {p.name: digest(p) for p in tools.values()},
                       "runtime_cargo_lock_sha256": digest(runtime / "Cargo.lock"),
                       "elaborator_cargo_lock_sha256": digest(elaborator / "Cargo.lock")}
            staged = cache / "installed.json.part"
            staged.write_text(json.dumps(receipt, indent=2) + "\n")
            staged.replace(cache / "installed.json")
            initialize_exercises(ROOT)
            print("\nSetup complete. Run ./koans.")
            return 0
    except KeyboardInterrupt:
        print("\nSetup interrupted. Run ./setup to continue from the cache.", file=sys.stderr)
        return 130
    except (CourseError, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"\nSetup failed: {exc}\nRun ./setup to retry; your exercise files are untouched.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
