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


def test_heading_text_is_normalized_and_grapheme_safe():
    source = APP_JS.read_text(encoding="utf-8")

    assert '.normalize(\'NFC\')' in source
    assert 'new Intl.Segmenter(language, { granularity: \'grapheme\' })' in source
    assert 'return [...segmenter.segment(normalizedText)].map((item) => item.segment);' in source
    assert 'normalizedText.match(/\\P{Mark}\\p{Mark}*|\\p{Mark}+/gu) || []' in source
    assert 'function normalizeHeadings()' in source
    assert 'document.querySelectorAll(\'h1, h2, h3\')' in source
    assert 'split(\'\')' not in source
    assert 'Array.from' not in source


def test_vietnamese_safe_font_stack_is_defined_for_all_content():
    styles = STYLE_CSS.read_text(encoding="utf-8")

    assert '@import url(\'https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro' in styles
    assert 'subset=vietnamese' in styles
    assert '--sans: "Be Vietnam Pro", "Noto Sans", Arial, sans-serif;' in styles
    assert '--serif: "Noto Serif", Georgia, "Times New Roman", serif;' in styles
    assert 'font-family: "Snell Roundhand"' not in styles
    assert 'font-family: Inter' not in styles


def test_paid_leave_unknown_value_is_preserved_in_frontend_payload():
    source = APP_JS.read_text(encoding="utf-8")

    assert "paidLeave: paidLeave === 'yes'" in source
    assert ": paidLeave," in source
    assert "paidLeave: paidLeave === 'yes' ? true : paidLeave === 'no' ? false : null" not in source


def test_analysis_submission_is_blocked_while_request_is_active():
    source = APP_JS.read_text(encoding="utf-8")

    assert "if (isAnalyzing) return;" in source
    assert "isAnalyzing = true;" in source


def test_issue_cards_use_localized_labels_and_humanize_unknown_types():
    source = APP_JS.read_text(encoding="utf-8")
    translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))

    assert "humanizeIssueType(item.issue)" in source
    assert "['result_issue_fact', item.fact_from_user]" in source
    assert "result.issue_fact" not in source
    assert translations["vi"]["issue_types"]["pay"] == "Tiền lương và thanh toán"
    assert translations["en"]["issue_types"]["pay"] == "Pay and wages"
    assert "issue_types" in translations["vi"] and "issue_types" in translations["en"]
    assert "replace(/[_-]+/g, ' ')" in source


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


def test_contract_and_payslip_choices_map_to_independent_nullable_flags():
    source = APP_JS.read_text(encoding="utf-8")
    template = (Path(__file__).parents[1] / "templates" / "index.html").read_text(encoding="utf-8")
    translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))

    for value in ("both", "payslip_only", "contract_only", "neither", "unsure"):
        assert f'value="{value}"' in template
    assert "has_contract: documentStatus.hasContract" in source
    assert "has_payslip: documentStatus.hasPayslip" in source
    assert "payslip_only: { hasContract: false, hasPayslip: true }" in source
    assert "contract_only: { hasContract: true, hasPayslip: false }" in source
    assert "neither: { hasContract: false, hasPayslip: false }" in source
    assert "unsure: { hasContract: null, hasPayslip: null }" in source
    assert translations["vi"]["opt_docs_payslip_only"] == "Không có hợp đồng nhưng có payslip"
    assert translations["en"]["opt_docs_contract_only"] == "I have a contract but no payslips"
