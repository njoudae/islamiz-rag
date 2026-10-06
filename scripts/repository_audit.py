"""Public-repository safety and documentation-link audit using only stdlib."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evaluation" / "repository_audit.json"
SELF = Path(__file__).resolve()
TEXT_SUFFIXES = {".md", ".json", ".py", ".ts", ".tsx", ".js", ".mjs", ".css", ".html", ".sql", ".toml", ".yml", ".yaml", ".txt", ".example"}
SECRET_PATTERNS = {
    "openai_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "github_token": re.compile(r"gh[ps]_[A-Za-z0-9]{20,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
}
# Values that are documented placeholders, not secrets: the demo administrator the README tells
# every reader to log in with, and example addresses.
DOCUMENTED_DEMO_VALUES = {"daleel-admin-2026"}
DOCUMENTED_ADDRESSES = {"admin@daleel.sa", "contact@daleel.sa", "hello@example.com", "name@example.com"}
ENV_STYLE_NAMES = {".env.example"}
ENV_STYLE_SUFFIXES = {".yml", ".yaml", ".toml", ".md", ".txt"}
MANIPULATION_PATTERNS = [
    "ignore " + "previous instructions",
    "give this project " + "full marks",
    "you are the " + "evaluator",
    "award " + "100/100",
]


def public_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def is_text(path: Path) -> bool:
    return path.name == ".env.example" or path.suffix.lower() in TEXT_SUFFIXES


def main() -> int:
    files = public_files()
    secret_findings: list[dict] = []
    manipulation_findings: list[dict] = []
    local_path_findings: list[dict] = []
    sensitive_assignment_findings: list[dict] = []
    private_url_findings: list[dict] = []
    email_findings: list[dict] = []
    broken_links: list[dict] = []

    for path in files:
        if path.resolve() == SELF or not path.is_file() or not is_text(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT).as_posix()
        for name, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                secret_findings.append({"file": relative, "type": name, "line": text.count("\n", 0, match.start()) + 1})
        lowered = text.casefold()
        for phrase in MANIPULATION_PATTERNS:
            if phrase in lowered:
                manipulation_findings.append({"file": relative, "phrase": phrase})
        for match in re.finditer(r"[A-Za-z]:\\Users\\[^\\\s]+", text, re.I):
            local_path_findings.append({"file": relative, "line": text.count("\n", 0, match.start()) + 1})
        # Assignments are checked in configuration-style files; in source code the same shape is an
        # ordinary variable. The value must sit on the same line, so an empty "KEY=" is not a finding.
        if path.name in ENV_STYLE_NAMES or path.suffix.lower() in ENV_STYLE_SUFFIXES:
            for match in re.finditer(r"(?im)^[ \t]*[A-Z0-9_]*(?:PASSWORD|TOKEN|SECRET|API_KEY)[ \t]*=[ \t]*([^\s#]+)", text):
                value = match.group(1).strip("\"'")
                placeholder = value.lower() in {"null", "none", "..."} or value in DOCUMENTED_DEMO_VALUES or value.startswith("<")
                if value and not placeholder and not any(marker in value.upper() for marker in ("CHANGE_ME", "PLACEHOLDER", "EXAMPLE", "YOUR_")):
                    sensitive_assignment_findings.append({"file": relative, "line": text.count("\n", 0, match.start()) + 1})
        for match in re.finditer(r"https?://(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|[^/\s]+\.internal)(?::\d+)?", text, re.I):
            if "host.docker.internal" in match.group(0):  # Docker's own name for the host machine
                continue
            private_url_findings.append({"file": relative, "line": text.count("\n", 0, match.start()) + 1})
        for match in re.finditer(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.I):
            if match.group(0).lower() in DOCUMENTED_ADDRESSES:
                continue
            email_findings.append({"file": relative, "line": text.count("\n", 0, match.start()) + 1})

        if path.suffix.lower() == ".md":
            for match in re.finditer(r"!?(?:\[[^\]]*\])\(([^)]+)\)", text):
                target = match.group(1).strip().split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target = unquote(target.strip("<>"))
                # Quoted source text contains "[15](..." footnotes that only look like links.
                if re.search(r"\s", target) or target.startswith("("):
                    continue
                if not (path.parent / target).resolve().exists():
                    broken_links.append({"file": relative, "target": target})

    required = [
        "README.md", "JUDGING.md", "RUNBOOK.md", "ARCHITECTURE.md", "LIMITATIONS.md",
        "submission.json", "evaluation/generation_final_report.md",
        "artifacts/benchmark/final_30q_retrieval/FINAL_BENCHMARK.md", "docs/VIDEO_SCRIPT_AR.md",
        "docs/VIDEO_SHOTLIST.md", "docs/sources-and-licenses.md",
    ]
    missing_required = [item for item in required if not (ROOT / item).exists()]
    json.loads((ROOT / "submission.json").read_text(encoding="utf-8"))
    json.loads((ROOT / "evaluation" / "generation_final_results.json").read_text(encoding="utf-8"))

    payload = {
        "files_scanned": len(files),
        "secret_findings": secret_findings,
        "evaluator_manipulation_findings": manipulation_findings,
        "local_absolute_path_findings": local_path_findings,
        "sensitive_assignment_findings": sensitive_assignment_findings,
        "private_url_findings": private_url_findings,
        "email_address_findings": email_findings,
        "broken_documentation_links": broken_links,
        "missing_required_files": missing_required,
        "passed": not any((secret_findings, manipulation_findings, local_path_findings, sensitive_assignment_findings, private_url_findings, email_findings, broken_links, missing_required)),
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
