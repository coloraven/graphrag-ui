from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
import shutil

from pypdf import PdfReader

from .paths import NORMALIZED_MANIFEST, NORMALIZED_PREFIX, NORMALIZED_SUFFIX, SUPPORTED_INPUT_EXTENSIONS


logger = logging.getLogger(__name__)


def build_normalized_name(source: Path) -> str:
    digest = hashlib.sha256(source.as_posix().encode("utf-8")).hexdigest()[:24]
    return f"{NORMALIZED_PREFIX}{digest}{NORMALIZED_SUFFIX}"



def load_normalized_manifest(normalized_dir: Path) -> dict[str, str]:
    manifest_path = normalized_dir / NORMALIZED_MANIFEST
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}



def restore_source_name(name: str, normalized_dir: Path | None = None) -> str:
    if normalized_dir is not None:
        manifest = load_normalized_manifest(normalized_dir)
        mapped_name = manifest.get(name)
        if mapped_name:
            return mapped_name
    return name


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text(extraction_mode="layout") or page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts).strip()


def normalize_documents(input_dir: Path, normalized_dir: Path) -> list[Path]:
    normalized_dir.mkdir(parents=True, exist_ok=True)
    for child in list(normalized_dir.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
            continue
        child.unlink()

    normalized_paths: list[Path] = []
    manifest: dict[str, str] = {}
    if not input_dir.exists():
        return normalized_paths

    for source in sorted(input_dir.rglob("*"), key=lambda item: str(item.relative_to(input_dir)).lower()):
        if not source.is_file() or source.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
            continue

        try:
            if source.suffix.lower() == ".pdf":
                content = extract_pdf_text(source)
            else:
                content = source.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Skipping unreadable document %s: %s", source, exc)
            continue

        if not content.strip():
            continue

        relative_name = source.relative_to(input_dir).as_posix()
        normalized_name = build_normalized_name(Path(relative_name))
        target = normalized_dir / normalized_name
        target.write_text(
            f"# {relative_name}\n\n{content.strip()}\n",
            encoding="utf-8",
        )
        manifest[normalized_name] = relative_name
        normalized_paths.append(target)

    (normalized_dir / NORMALIZED_MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return normalized_paths
