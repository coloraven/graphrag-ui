from __future__ import annotations

import logging
from pathlib import Path

from reggraph_assistant.preprocess import normalize_documents


def test_normalize_documents_logs_and_skips_unreadable_file(tmp_path: Path, caplog) -> None:
    input_dir = tmp_path / 'input'
    normalized_dir = tmp_path / 'normalized'
    input_dir.mkdir()

    good_file = input_dir / 'good.md'
    bad_file = input_dir / 'bad.md'
    good_file.write_text('# Good\n\ncontent', encoding='utf-8')
    bad_file.write_bytes(b'\xff\xfe\x00\x00')

    with caplog.at_level(logging.WARNING):
        normalized = normalize_documents(input_dir, normalized_dir)

    assert len(normalized) == 1
    assert normalized[0].read_text(encoding='utf-8').startswith('# good.md')
    assert 'Skipping unreadable document' in caplog.text
