from clearcue.documents.ingest import chunk_text


def test_chunk_text_preserves_content_with_overlap() -> None:
    words = [f"word{index}" for index in range(400)]
    chunks = chunk_text(" ".join(words), words_per_chunk=100, overlap=20)
    assert len(chunks) == 5
    assert chunks[0].split()[80] == chunks[1].split()[0]
    assert words[-1] in chunks[-1]


def test_chunk_empty_text() -> None:
    assert chunk_text("  ") == []

