"""A company board deck is accepted only when it is a PowerPoint with slides."""

from io import BytesIO

from pptx import Presentation

from app.services.close_context.slide_deck_template import SlideDeckRejected, inspect_slide_deck


def _pptx_bytes(slides: int = 1) -> bytes:
    presentation = Presentation()
    for _ in range(slides):
        presentation.slides.add_slide(presentation.slide_layouts[6])
    buf = BytesIO()
    presentation.save(buf)
    return buf.getvalue()


def test_inspect_counts_slides_and_hashes_the_file() -> None:
    raw = _pptx_bytes(2)
    facts = inspect_slide_deck(raw, r"C:\decks\Board Review.pptx")
    assert facts["filename"] == "Board Review.pptx"
    assert facts["slide_count"] == 2
    assert facts["byte_size"] == len(raw)
    assert len(str(facts["sha256"])) == 64


def test_inspect_rejects_a_file_that_is_not_a_deck() -> None:
    try:
        inspect_slide_deck(b"not a deck", "notes.pptx")
    except SlideDeckRejected as exc:
        assert "not a PowerPoint" in exc.message
    else:
        raise AssertionError("expected rejection")


def test_inspect_rejects_the_wrong_kind_of_file() -> None:
    try:
        inspect_slide_deck(_pptx_bytes(), "Actual_MRR_Waterfall.csv")
    except SlideDeckRejected as exc:
        assert ".pptx" in exc.message
    else:
        raise AssertionError("expected rejection")
