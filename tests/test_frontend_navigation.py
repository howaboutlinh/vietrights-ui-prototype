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


def test_pay_frequency_labels_and_dynamic_amount_placeholders_switch_between_languages():
    translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))

    assert [translations["vi"][key] for key in ("opt_pay_hourly", "opt_pay_daily", "opt_pay_weekly", "opt_pay_fortnightly")] == ["Theo giờ", "Theo ngày", "Theo tuần", "Theo hai tuần"]
    assert [translations["en"][key] for key in ("opt_pay_hourly", "opt_pay_daily", "opt_pay_weekly", "opt_pay_fortnightly")] == ["Hourly", "Daily", "Weekly", "Fortnightly"]
    assert [translations["vi"]["pay_labels"][key] for key in ("hourly", "per_shift", "daily", "weekly", "fortnightly")] == [
        "Bạn được trả bao nhiêu mỗi giờ?", "Bạn được trả bao nhiêu mỗi ca?", "Bạn được trả bao nhiêu mỗi ngày?",
        "Bạn được trả bao nhiêu mỗi tuần?", "Bạn được trả bao nhiêu mỗi hai tuần?"
    ]
    assert [translations["en"]["pay_labels"][key] for key in ("hourly", "per_shift", "daily", "weekly", "fortnightly")] == [
        "How much are you paid per hour?", "How much are you paid per shift?", "How much are you paid per day?",
        "How much are you paid per week?", "How much are you paid per fortnight?"
    ]
    assert translations["vi"]["pay_amount_placeholders"] == {
        "hourly": "Ví dụ: 26.44", "per_shift": "Ví dụ: 211.52", "daily": "Ví dụ: 200.94", "weekly": "Ví dụ: 1004.90", "fortnightly": "Ví dụ: 2009.80"
    }
    assert translations["en"]["pay_amount_placeholders"] == {
        "hourly": "Example: 26.44", "per_shift": "Example: 211.52", "daily": "Example: 200.94", "weekly": "Example: 1004.90", "fortnightly": "Example: 2009.80"
    }
    assert "pay_frequency_note" not in translations["vi"]
    assert "pay_frequency_note" not in translations["en"]
    assert "pay_amount_placeholders.${value}" in APP_JS.read_text(encoding="utf-8")
