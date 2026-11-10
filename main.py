from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from flask import Flask, jsonify, render_template, request


ROOT = Path(__file__).resolve().parent
SOLUTIONS_DIR = ROOT / "solutions"
WORKSPACE_DIR = ROOT / "workspace"
SETTINGS_DIR = ROOT / "settings"
CURRENT_SOLUTION_FILE = SETTINGS_DIR / "current_solution.json"
STUDENT_FILE = SETTINGS_DIR / "current_student.json"
MAPPINGS_FILE = SETTINGS_DIR / "comparisons.json"
RUN_TIMEOUT_SECONDS = 15

for directory in (SOLUTIONS_DIR, WORKSPACE_DIR, SETTINGS_DIR):
    directory.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


def read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def current_solution() -> dict[str, Any] | None:
    return read_json(CURRENT_SOLUTION_FILE, None)


def current_student() -> dict[str, Any]:
    return read_json(STUDENT_FILE, {"name": "", "student_id": "", "archive_name": ""})


def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    """Extract ordinary assignment files, ignoring macOS archive metadata."""
    destination_resolved = destination.resolve()
    for item in archive.infolist():
        name = item.filename.replace("\\", "/")
        posix_name = PurePosixPath(name)
        if posix_name.is_absolute() or ".." in posix_name.parts:
            continue
        if any(part in {"__MACOSX", "__pycache__"} for part in posix_name.parts):
            continue
        if posix_name.name in {".DS_Store", ".gitkeep"} or not posix_name.parts:
            continue

        output = destination.joinpath(*posix_name.parts)
        if not output.resolve().is_relative_to(destination_resolved):
            continue
        if item.is_dir():
            output.mkdir(parents=True, exist_ok=True)
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(item) as source, output.open("wb") as target:
            shutil.copyfileobj(source, target)


def list_files(directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name not in {".DS_Store", ".gitkeep"}
    )


def mappings_for_solution(solution: dict[str, Any] | None) -> list[dict[str, str]]:
    if not solution:
        return []
    all_mappings = read_json(MAPPINGS_FILE, {})
    return all_mappings.get(solution.get("archive_hash", ""), [])


def get_state() -> dict[str, Any]:
    solution = current_solution()
    return {
        "solution": solution,
        "solution_files": list_files(SOLUTIONS_DIR),
        "student": current_student(),
        "student_files": list_files(WORKSPACE_DIR),
        "comparisons": mappings_for_solution(solution),
    }


def clean_extract_directory(directory: Path) -> None:
    for child in directory.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    return jsonify(get_state())


@app.post("/api/solutions/extract")
def extract_solution():
    uploaded = request.files.get("archive")
    if uploaded is None or not uploaded.filename:
        return jsonify(error="Choose a solution ZIP file first."), 400
    if Path(uploaded.filename).suffix.lower() != ".zip":
        return jsonify(error="The solution upload must be a ZIP file."), 400

    content = uploaded.read()
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            damaged_member = archive.testzip()
            if damaged_member:
                return jsonify(error=f"The ZIP contains a damaged file: {damaged_member}"), 400
            clean_extract_directory(SOLUTIONS_DIR)
            safe_extract(archive, SOLUTIONS_DIR)
    except (zipfile.BadZipFile, OSError) as error:
        return jsonify(error=f"Could not extract that ZIP: {error}"), 400

    solution = {
        "archive_name": Path(uploaded.filename).name,
        "archive_hash": hashlib.sha256(content).hexdigest(),
    }
    write_json(CURRENT_SOLUTION_FILE, solution)
    return jsonify(get_state())


@app.post("/api/student/extract")
def extract_student():
    uploaded = request.files.get("archive")
    if uploaded is None or not uploaded.filename:
        return jsonify(error="Choose a student ZIP file first."), 400
    if Path(uploaded.filename).suffix.lower() != ".zip":
        return jsonify(error="The student upload must be a ZIP file."), 400

    content = uploaded.read()
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            damaged_member = archive.testzip()
            if damaged_member:
                return jsonify(error=f"The ZIP contains a damaged file: {damaged_member}"), 400
            clean_extract_directory(WORKSPACE_DIR)
            safe_extract(archive, WORKSPACE_DIR)
    except (zipfile.BadZipFile, OSError) as error:
        return jsonify(error=f"Could not extract that ZIP: {error}"), 400

    student = {
        "name": request.form.get("name", "").strip(),
        "student_id": request.form.get("student_id", "").strip(),
        "archive_name": Path(uploaded.filename).name,
    }
    write_json(STUDENT_FILE, student)
    return jsonify(get_state())


@app.post("/api/comparisons")
def save_comparisons():
    solution = current_solution()
    if not solution:
        return jsonify(error="Extract a solution ZIP before saving comparisons."), 400
    payload = request.get_json(silent=True) or {}
    rows = payload.get("comparisons", [])
    if not isinstance(rows, list):
        return jsonify(error="Comparisons must be a list."), 400

    solution_files = set(list_files(SOLUTIONS_DIR))
    student_files = set(list_files(WORKSPACE_DIR))
    normalized: list[dict[str, str]] = []
    for row in rows:
        solution_file = str(row.get("solution_file", ""))
        student_file = str(row.get("student_file", ""))
        if solution_file not in solution_files or student_file not in student_files:
            return jsonify(error="Each comparison must use files that exist in both file lists."), 400
        normalized.append({"solution_file": solution_file, "student_file": student_file})

    all_mappings = read_json(MAPPINGS_FILE, {})
    all_mappings[solution["archive_hash"]] = normalized
    write_json(MAPPINGS_FILE, all_mappings)
    return jsonify(comparisons=normalized)


def run_python_file(directory: Path, relative_file: str) -> dict[str, Any]:
    candidate = (directory / relative_file).resolve()
    if not candidate.is_relative_to(directory.resolve()) or not candidate.is_file():
        return {"ok": False, "stdout": b"", "stderr": b"Invalid file path.", "error": "Invalid file path."}

    try:
        result = subprocess.run(
            [sys.executable, str(candidate)],
            cwd=str(candidate.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=RUN_TIMEOUT_SECONDS,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": None if result.returncode == 0 else f"Process exited with code {result.returncode}.",
        }
    except subprocess.TimeoutExpired as error:
        return {
            "ok": False,
            "stdout": error.stdout or b"",
            "stderr": error.stderr or b"",
            "error": f"Timed out after {RUN_TIMEOUT_SECONDS} seconds.",
        }
    except OSError as error:
        return {"ok": False, "stdout": b"", "stderr": str(error).encode(), "error": str(error)}


def display_bytes(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


@app.post("/api/run")
def run_comparisons():
    state = get_state()
    if not state["solution"] or not state["student_files"]:
        return jsonify(error="Extract both a solution ZIP and a student ZIP before running."), 400
    comparisons = state["comparisons"]
    if not comparisons:
        return jsonify(error="Add and save at least one comparison first."), 400

    results = []
    for row in comparisons:
        expected = run_python_file(SOLUTIONS_DIR, row["solution_file"])
        actual = run_python_file(WORKSPACE_DIR, row["student_file"])
        both_completed = expected["ok"] and actual["ok"]
        match = both_completed and expected["stdout"] == actual["stdout"]
        results.append(
            {
                **row,
                "status": "MATCH" if match else ("MISMATCH" if both_completed else "RUN ERROR"),
                "expected": display_bytes(expected["stdout"]),
                "actual": display_bytes(actual["stdout"]),
                "expected_stderr": display_bytes(expected["stderr"]),
                "actual_stderr": display_bytes(actual["stderr"]),
                "expected_error": expected["error"],
                "actual_error": actual["error"],
            }
        )
    return jsonify(student=state["student"], results=results)


if __name__ == "__main__":
    app.run(debug=True)
