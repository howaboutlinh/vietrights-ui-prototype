from pathlib import Path


APP_JS = Path(__file__).parents[1] / "static" / "js" / "app.js"
STYLE_CSS = Path(__file__).parents[1] / "static" / "css" / "style.css"


def test_successful_next_and_back_transitions_scroll_questionnaire_card():
    source = APP_JS.read_text(encoding="utf-8")

    assert "showStep(currentStep + 1, { scroll: true });" in source
    assert "showStep(currentStep - 1, { scroll: true });" in source
    assert "function scrollQuestionnaireIntoView()" in source
    assert "requestAnimationFrame(() =>" in source
    assert "intakeCard.scrollIntoView({" in source
    assert "block: 'start'" in source


def test_questionnaire_scroll_respects_reduced_motion_and_clears_sources_hash():
    source = APP_JS.read_text(encoding="utf-8")
    styles = STYLE_CSS.read_text(encoding="utf-8")

    assert "window.matchMedia?.('(prefers-reduced-motion: reduce)').matches" in source
    assert "clearSourcesHashForQuestionnaire();" in source
    assert "history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);" in source
    assert "scroll-margin-top: 100px;" in styles
