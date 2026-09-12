from pathlib import Path
import json


APP_JS = Path(__file__).parents[1] / "static" / "js" / "app.js"
STYLE_CSS = Path(__file__).parents[1] / "static" / "css" / "style.css"
TRANSLATIONS = Path(__file__).parents[1] / "static" / "locales" / "translations.json"


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


def test_pay_frequency_labels_and_notes_switch_between_languages():
    translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))

    assert translations["vi"]["opt_pay_hourly"] == "Theo giờ — Ví dụ: $26.44/giờ"
    assert translations["vi"]["opt_pay_daily"] == "Theo ngày — Ví dụ: $200.94/ngày"
    assert translations["vi"]["opt_pay_weekly"] == "Theo tuần — Ví dụ: $1,004.90/tuần"
    assert translations["vi"]["opt_pay_fortnightly"] == "Theo hai tuần — Ví dụ: $2,009.80 mỗi hai tuần"
    assert translations["en"]["opt_pay_hourly"] == "Hourly — Example: $26.44 per hour"
    assert translations["en"]["opt_pay_daily"] == "Daily — Example: $200.94 per day"
    assert translations["en"]["opt_pay_weekly"] == "Weekly — Example: $1,004.90 per week"
    assert translations["en"]["opt_pay_fortnightly"] == "Fortnightly — Example: $2,009.80 per fortnight"
    assert translations["vi"]["pay_frequency_note"]
    assert translations["en"]["pay_frequency_note"]
