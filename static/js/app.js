const choiceButtons = [...document.querySelectorAll('.choice')];
const error = document.getElementById('error');
const questionView = document.getElementById('question-view');
const resultView = document.getElementById('result-view');
const documentsAvailableField = document.getElementById('documentsAvailable');
const casualShownOnDocumentsField = document.getElementById('casualShownOnDocuments');
const casualQuestionGroup = casualShownOnDocumentsField && (
    casualShownOnDocumentsField.closest ? casualShownOnDocumentsField.closest('.field-group') : casualShownOnDocumentsField.parentElement
);
const mainIssueField = document.getElementById('mainIssue');

const UNKNOWN_VALUES = new Set(['unknown', 'not_sure', 'no_info', 'no_data']);

function clearFieldErrors() {
    document.querySelectorAll('.field-error').forEach((node) => {
        node.textContent = '';
        node.style.display = 'none';
    });
}

function showFieldError(id, message) {
    const node = document.getElementById(id);
    if (!node) {
        return;
    }

    node.textContent = message;
    node.style.display = 'block';
}

function isExplicitUnknown(value) {
    if (value === null || value === undefined) return false;
    return UNKNOWN_VALUES.has(String(value).trim().toLowerCase()) || String(value).trim() === 'Không biết' || String(value).trim() === 'Không chắc' || String(value).trim() === 'Không có thông tin này';
}

function fieldIsAnswered(value) {
    if (value === null || value === undefined) return false;
    const text = String(value).trim();
    return text !== '' && !isExplicitUnknown(text);
}

function hasSelectedWorkTime() {
    return choiceButtons.some((button) => button.getAttribute('aria-pressed') === 'true');
}

function updateCasualDocumentVisibility() {
    if (!documentsAvailableField || !casualShownOnDocumentsField || !casualQuestionGroup) {
        return;
    }

    const availability = documentsAvailableField.value;
    const shouldShowCasualQuestion = availability === 'yes' || availability === 'no_contract' || availability === 'no_payslip';

    if (shouldShowCasualQuestion) {
        casualQuestionGroup.style.display = '';
    } else {
        casualQuestionGroup.style.display = 'none';
        casualShownOnDocumentsField.value = '';
    }
}

function getMainIssue() {
    if (!mainIssueField) return '';
    return String(mainIssueField.value || '').trim().toLowerCase();
}

function validateContextualFields() {
    clearFieldErrors();

    let valid = true;
    const mainIssue = getMainIssue();

    const workplaceValue = document.getElementById('workplace')?.value || '';
    const visaThreatValue = document.getElementById('visaThreat')?.value || '';
    const workPatternValue = document.getElementById('workPattern')?.value || '';
    const overtimeValue = document.getElementById('overtimeStatus')?.value || '';
    const breakValue = document.getElementById('breakStatus')?.value || '';
    const hoursPerWeekValue = document.getElementById('hoursPerWeek')?.value || '';
    const hourlyPayValue = document.getElementById('hourlyPay')?.value || '';
    const payslipStatusValue = document.getElementById('payslipStatus')?.value || '';
    const hourlyPayStatusValue = document.getElementById('hourlyPayStatus')?.value || '';
    const hoursPerWeekStatusValue = document.getElementById('hoursPerWeekStatus')?.value || '';

    if (!workplaceValue) {
        showFieldError('workplaceError', 'Vui lòng chọn môi trường làm việc.');
        valid = false;
    }

    if (!workPatternValue) {
        showFieldError('workPatternError', 'Vui lòng chọn kiểu làm việc.');
        valid = false;
    }

    if (!visaThreatValue) {
        showFieldError('visaThreatError', 'Vui lòng cho biết tình trạng visa.');
        valid = false;
    }

    if (!hasSelectedWorkTime()) {
        showFieldError('workTimeError', 'Vui lòng chọn ít nhất một thời điểm làm việc.');
        valid = false;
    }

    const payIssues = ['pay_underpayment', 'documents_contract'];
    const hoursIssues = ['hours_overtime'];
    const isPayIssue = payIssues.includes(mainIssue);
    const isHoursIssue = hoursIssues.includes(mainIssue);

    if (isPayIssue) {
        const hasHourlyPay = fieldIsAnswered(hourlyPayValue) || (hourlyPayStatusValue && isExplicitUnknown(hourlyPayStatusValue));
        const hasHoursPerWeek = fieldIsAnswered(hoursPerWeekValue) || (hoursPerWeekStatusValue && isExplicitUnknown(hoursPerWeekStatusValue));

        if (!hasHourlyPay) {
            showFieldError('hourlyPayError', 'Vui lòng nhập mức lương theo giờ hoặc chọn “Không biết”.');
            valid = false;
        }

        if (!hasHoursPerWeek) {
            showFieldError('hoursPerWeekError', 'Vui lòng nhập số giờ làm mỗi tuần hoặc chọn “Không biết”.');
            valid = false;
        }

        if (!payslipStatusValue) {
            showFieldError('payslipStatusError', 'Vui lòng cho biết bạn có nhận payslip không.');
            valid = false;
        }
    }

    if (isHoursIssue) {
        const hasHoursPerWeek = fieldIsAnswered(hoursPerWeekValue) || (hoursPerWeekStatusValue && isExplicitUnknown(hoursPerWeekStatusValue));

        if (!hasHoursPerWeek) {
            showFieldError('hoursPerWeekError', 'Vui lòng nhập số giờ làm mỗi tuần hoặc chọn “Không biết”.');
            valid = false;
        }

        if (!overtimeValue) {
            showFieldError('overtimeStatusError', 'Vui lòng cho biết bạn có làm thêm giờ không.');
            valid = false;
        }

        if (!breakValue) {
            showFieldError('breakStatusError', 'Vui lòng cho biết bạn có được nghỉ giữa ca không.');
            valid = false;
        }
    }

    if (mainIssue === 'pay_underpayment' || mainIssue === 'hours_overtime') {
        const hasPayInfo = fieldIsAnswered(hourlyPayValue) || (hourlyPayStatusValue && isExplicitUnknown(hourlyPayStatusValue));
        const hasWeekInfo = fieldIsAnswered(hoursPerWeekValue) || (hoursPerWeekStatusValue && isExplicitUnknown(hoursPerWeekStatusValue));
        if (!hasPayInfo && !hasWeekInfo && !isPayIssue && !isHoursIssue) {
            // no-op; branch handled above
        }
    }

    return valid;
}

function collectCaseData() {
    const getTextValue = (id) => {
        const field = document.getElementById(id);
        if (!field || field.value === undefined || field.value === null) return null;
        const value = field.value.trim();
        return value !== '' ? value : null;
    };

    const getNumberValue = (id) => {
        const value = getTextValue(id);
        if (value === null) return null;
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    };

    const selectedWorkTimes = [...document.querySelectorAll('.choice[aria-pressed="true"]')]
        .map((button) => button.querySelector('strong')?.textContent?.trim())
        .filter(Boolean);

    const mainIssue = getTextValue('mainIssue') || 'other';
    const explicitEmploymentType = getTextValue('employmentType');
    const workPattern = getTextValue('workPattern') || 'unknown';
    const paidLeaveValue = getTextValue('paidLeave');
    const documentsAvailableValue = getTextValue('documentsAvailable');
    const casualValue = getTextValue('casualShownOnDocuments');
    const hourlyPayConfirmedValue = getTextValue('hourlyPayConfirmed');
    const payslipStatusValue = getTextValue('payslipStatus');
    const paymentMethodValue = getTextValue('paymentMethod');
    const overtimeStatusValue = getTextValue('overtimeStatus');
    const breakStatusValue = getTextValue('breakStatus');

    const documentAvailability = documentsAvailableValue === 'no_both' ? 'none' : (documentsAvailableValue || 'unknown');
    const shouldShowCasualQuestion = ['yes', 'no_contract', 'no_payslip'].includes(documentsAvailableValue || '');
    const casualShownOnDocuments = shouldShowCasualQuestion ? (casualValue || 'unknown') : 'unknown';

    return {
        mainIssue,
        workplace: getTextValue('workplace'),
        employmentType: explicitEmploymentType || 'unknown',
        workTime: selectedWorkTimes,
        description: getTextValue('description'),
        overtimeStatus: overtimeStatusValue || 'unknown',
        breakStatus: breakStatusValue || 'unknown',
        hoursPerWeek: getNumberValue('hoursPerWeek'),
        hoursPerShift: getNumberValue('hoursPerShift'),
        visaThreat: getTextValue('visaThreat'),
        documentAvailability,
        casualShownOnDocuments,
        employmentPattern: {
            workPattern,
            hoursPerWeek: getNumberValue('hoursPerWeek'),
            hoursPerShift: getNumberValue('hoursPerShift'),
            paidLeave: paidLeaveValue === 'yes' ? true : paidLeaveValue === 'no' ? false : null,
            documentAvailability,
            casualShownOnDocuments,
            overtimeStatus: overtimeStatusValue || 'unknown',
            breakStatus: breakStatusValue || 'unknown'
        },
        pay: {
            hourlyPay: getNumberValue('hourlyPay'),
            hourlyPayConfirmed: hourlyPayConfirmedValue === 'yes' ? true : hourlyPayConfirmedValue === 'no' ? false : 'unknown',
            payslipStatus: payslipStatusValue || 'unknown',
            paymentMethod: paymentMethodValue || 'unknown'
        }
    };
}

function renderListItems(listElement, items) {
    if (!listElement) {
        return;
    }

    listElement.innerHTML = '';

    const values = Array.isArray(items) ? items : [];
    const cleaned = values.filter((item) => item !== null && item !== undefined && String(item).trim() !== '');

    if (cleaned.length === 0) {
        listElement.closest('[id$="Wrap"]')?.setAttribute('style', 'display: none;');
        return;
    }

    cleaned.forEach((item) => {
        const listItem = document.createElement('li');
        listItem.textContent = String(item);
        listElement.appendChild(listItem);
    });

    listElement.closest('[id$="Wrap"]')?.removeAttribute('style');
}

function renderResult(result) {
    if (!result || typeof result !== 'object') {
        return;
    }

    const resultTitle = document.getElementById('resultTitle');
    const resultSummary = document.getElementById('resultSummary');
    const resultIssues = document.getElementById('resultIssues');
    const resultEvidence = document.getElementById('resultEvidence');
    const resultNextSteps = document.getElementById('resultNextSteps');
    const resultSources = document.getElementById('resultSources');
    const resultRiskLevel = document.getElementById('resultRiskLevel');

    if (resultTitle) {
        resultTitle.textContent = 'Kết quả kiểm tra';
    }

    if (resultSummary) {
        const summaryText = typeof result.summary === 'string' ? result.summary.trim() : '';
        if (summaryText) {
            resultSummary.textContent = summaryText;
            resultSummary.style.display = '';
        } else {
            resultSummary.textContent = '';
            resultSummary.style.display = 'none';
        }
    }

    if (resultRiskLevel) {
        const riskLevel = result.risk_level;
        const riskText = typeof riskLevel === 'string' && riskLevel.trim() ? riskLevel.trim() : '';
        if (riskText) {
            resultRiskLevel.textContent = '● Mức độ cần chú ý: ' + riskText;
            resultRiskLevel.style.display = '';
        } else {
            resultRiskLevel.textContent = '';
            resultRiskLevel.style.display = 'none';
        }
    }

    const issues = Array.isArray(result.issues) ? result.issues : [];
    const evidence = Array.isArray(result.evidence) ? result.evidence : [];
    const nextSteps = Array.isArray(result.next_steps) ? result.next_steps : [];
    const sources = Array.isArray(result.sources) ? result.sources : [];

    renderListItems(resultIssues, issues);
    renderListItems(resultEvidence, evidence);
    renderListItems(resultNextSteps, nextSteps);

    const issueWrap = document.getElementById('resultIssuesWrap');
    const evidenceWrap = document.getElementById('resultEvidenceWrap');
    const nextStepsWrap = document.getElementById('resultNextStepsWrap');

    if (issueWrap) {
        issueWrap.style.display = resultIssues && resultIssues.children.length ? '' : 'none';
    }
    if (evidenceWrap) {
        evidenceWrap.style.display = resultEvidence && resultEvidence.children.length ? '' : 'none';
    }
    if (nextStepsWrap) {
        nextStepsWrap.style.display = resultNextSteps && resultNextSteps.children.length ? '' : 'none';
    }

    if (resultSources) {
        const sourceText = sources.filter((item) => item !== null && item !== undefined && String(item).trim() !== '').join('; ');
        if (sourceText) {
            resultSources.textContent = 'Nguồn: ' + sourceText;
            resultSources.style.display = '';
        } else {
            resultSources.textContent = '';
            resultSources.style.display = 'none';
        }
    }
}

if (documentsAvailableField && typeof documentsAvailableField.addEventListener === 'function') {
    documentsAvailableField.addEventListener('change', updateCasualDocumentVisibility);
}

updateCasualDocumentVisibility();

choiceButtons.forEach((button) => {
    button.addEventListener('click', () => {
        const selected = button.getAttribute('aria-pressed') === 'true';
        button.setAttribute('aria-pressed', String(!selected));
        error.style.display = 'none';
    });
});

document.getElementById('continue').addEventListener('click', async () => {
    clearFieldErrors();

    if (!validateContextualFields()) {
        error.style.display = 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
    }

    error.style.display = 'none';

    try {
        const result = await sendCaseToBackend();

        console.log("Analysis result:", result);

        renderResult(result);
        questionView.style.display = 'none';
        resultView.style.display = 'block';

        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });

    } catch (error) {
        console.error("Failed to analyze case:", error);
    }
});

document.getElementById('edit').addEventListener('click', () => {
    resultView.style.display = 'none';
    questionView.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

async function sendCaseToBackend() {
    const caseData = collectCaseData();

    const response = await fetch("/analyze", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(caseData)
    });

    const result = await response.json();

    console.log("Backend response:", result);
    return result;
}