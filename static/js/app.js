const choiceButtons = [...document.querySelectorAll('.choice')];
const error = document.getElementById('error');
const questionView = document.getElementById('question-view');
const resultView = document.getElementById('result-view');
const documentsAvailableField = document.getElementById('documentsAvailable');
const employmentTypeOnDocumentsField = document.getElementById('employmentTypeOnDocuments');
const employmentTypeOnDocumentsGroup = employmentTypeOnDocumentsField && (
    employmentTypeOnDocumentsField.closest ? employmentTypeOnDocumentsField.closest('.field-group') : employmentTypeOnDocumentsField.parentElement
);
const workplaceField = document.getElementById('workplace');
const workplaceOtherField = document.getElementById('workplaceOther');
const workplaceOtherGroup = document.getElementById('workplaceOtherGroup');
const payBasisField = document.getElementById('payBasis');
const payAmountField = document.getElementById('payAmount');
const payAmountGroup = document.getElementById('payAmountGroup');
const payAmountLabel = document.getElementById('payAmountLabel');
const payPieceworkDescriptionField = document.getElementById('payPieceworkDescription');
const payPieceworkDescriptionGroup = document.getElementById('payPieceworkDescriptionGroup');
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

function updateEmploymentTypeOnDocumentsVisibility() {
    if (!documentsAvailableField || !employmentTypeOnDocumentsField || !employmentTypeOnDocumentsGroup) {
        return;
    }

    const availability = documentsAvailableField.value;
    const shouldShowEmploymentTypeQuestion = availability === 'yes' || availability === 'no_contract' || availability === 'no_payslip';

    if (shouldShowEmploymentTypeQuestion) {
        employmentTypeOnDocumentsGroup.style.display = '';
    } else {
        employmentTypeOnDocumentsGroup.style.display = 'none';
        employmentTypeOnDocumentsField.value = 'unknown';
    }
}

function updateWorkplaceVisibility() {
    if (!workplaceField || !workplaceOtherField || !workplaceOtherGroup) {
        return;
    }

    if (workplaceField.value === 'other') {
        workplaceOtherGroup.style.display = '';
    } else {
        workplaceOtherGroup.style.display = 'none';
        workplaceOtherField.value = '';
    }
}

function updatePayBasisVisibility() {
    if (!payBasisField || !payAmountGroup || !payAmountLabel || !payPieceworkDescriptionGroup) {
        return;
    }

    const payBasis = payBasisField.value;
    const amountQuestions = {
        hourly: 'Bạn được trả bao nhiêu cho mỗi giờ làm việc?',
        per_shift: 'Bạn được trả bao nhiêu cho mỗi ca?',
        daily: 'Bạn được trả bao nhiêu cho mỗi ngày làm việc?',
        weekly: 'Bạn được trả bao nhiêu mỗi tuần?',
        monthly: 'Bạn được trả bao nhiêu mỗi tháng?'
    };

    if (payBasis && amountQuestions[payBasis]) {
        payAmountGroup.style.display = '';
        payAmountLabel.textContent = amountQuestions[payBasis];
        payPieceworkDescriptionGroup.style.display = 'none';
        if (payPieceworkDescriptionField) {
            payPieceworkDescriptionField.value = '';
        }
    } else if (payBasis === 'piecework') {
        payAmountGroup.style.display = 'none';
        payPieceworkDescriptionGroup.style.display = '';
        if (payAmountField) {
            payAmountField.value = '';
        }
    } else {
        payAmountGroup.style.display = 'none';
        payPieceworkDescriptionGroup.style.display = 'none';
        if (payAmountField) {
            payAmountField.value = '';
        }
        if (payPieceworkDescriptionField) {
            payPieceworkDescriptionField.value = '';
        }
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
    const workplaceOtherValue = document.getElementById('workplaceOther')?.value || '';
    const visaThreatValue = document.getElementById('visaThreat')?.value || '';
    const workPatternValue = document.getElementById('workPattern')?.value || '';
    const overtimeValue = document.getElementById('overtimeStatus')?.value || '';
    const breakValue = document.getElementById('breakStatus')?.value || '';
    const hoursPerWeekValue = document.getElementById('hoursPerWeek')?.value || '';
    const payBasisValue = document.getElementById('payBasis')?.value || '';
    const payAmountValue = document.getElementById('payAmount')?.value || '';
    const payPieceworkDescriptionValue = document.getElementById('payPieceworkDescription')?.value || '';
    const payslipStatusValue = document.getElementById('payslipStatus')?.value || '';
    const hoursPerWeekStatusValue = document.getElementById('hoursPerWeekStatus')?.value || '';

    if (!workplaceValue) {
        showFieldError('workplaceError', 'Vui lòng chọn môi trường làm việc.');
        valid = false;
    }

    if (workplaceValue === 'other' && !fieldIsAnswered(workplaceOtherValue)) {
        showFieldError('workplaceOtherError', 'Vui lòng ghi rõ môi trường làm việc của bạn.');
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

    if (!payBasisValue) {
        showFieldError('payBasisError', 'Vui lòng chọn cách bạn được trả lương.');
        valid = false;
    }

    if (['hourly', 'per_shift', 'daily', 'weekly', 'monthly'].includes(payBasisValue) && !fieldIsAnswered(payAmountValue)) {
        showFieldError('payAmountError', 'Vui lòng nhập số tiền phù hợp với cách trả lương bạn đã chọn.');
        valid = false;
    }

    if (payBasisValue === 'piecework' && !fieldIsAnswered(payPieceworkDescriptionValue)) {
        showFieldError('payPieceworkDescriptionError', 'Vui lòng mô tả ngắn cách tính lương theo sản phẩm hoặc công việc.');
        valid = false;
    }

    if (isPayIssue) {
        const hasHoursPerWeek = fieldIsAnswered(hoursPerWeekValue) || (hoursPerWeekStatusValue && isExplicitUnknown(hoursPerWeekStatusValue));

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
        const hasPayInfo = ['hourly', 'per_shift', 'daily', 'weekly', 'monthly'].includes(payBasisValue) && fieldIsAnswered(payAmountValue);
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
    const workPattern = getTextValue('workPattern') || 'unknown';
    const paidLeaveValue = getTextValue('paidLeave');
    const documentsAvailableValue = getTextValue('documentsAvailable');
    const employmentTypeOnDocumentsValue = getTextValue('employmentTypeOnDocuments');
    const workplaceValue = getTextValue('workplace');
    const workplaceOtherValue = getTextValue('workplaceOther');
    const payBasisValue = getTextValue('payBasis') || 'unknown';
    const payAmountValue = getNumberValue('payAmount');
    const overtimeStatusValue = getTextValue('overtimeStatus');
    const breakStatusValue = getTextValue('breakStatus');

    const documentAvailability = documentsAvailableValue === 'no_both' ? 'none' : (documentsAvailableValue || 'unknown');
    const shouldShowEmploymentTypeQuestion = ['yes', 'no_contract', 'no_payslip'].includes(documentsAvailableValue || '');
    const employmentTypeOnDocuments = shouldShowEmploymentTypeQuestion ? (employmentTypeOnDocumentsValue || 'unknown') : 'unknown';

    const payload = {
        mainIssue,
        workplace: workplaceValue === 'other' && workplaceOtherValue ? 'other' : (workplaceValue || 'unknown'),
        workTime: selectedWorkTimes,
        description: getTextValue('description'),
        overtimeStatus: overtimeStatusValue || 'unknown',
        breakStatus: breakStatusValue || 'unknown',
        hoursPerWeek: getNumberValue('hoursPerWeek'),
        hoursPerShift: getNumberValue('hoursPerShift'),
        visaThreat: getTextValue('visaThreat'),
        documentAvailability,
        employmentTypeOnDocuments,
        employmentPattern: {
            workPattern,
            hoursPerWeek: getNumberValue('hoursPerWeek'),
            hoursPerShift: getNumberValue('hoursPerShift'),
            paidLeave: paidLeaveValue === 'yes' ? true : paidLeaveValue === 'no' ? false : null,
            documentAvailability,
            employmentTypeOnDocuments,
            overtimeStatus: overtimeStatusValue || 'unknown',
            breakStatus: breakStatusValue || 'unknown'
        },
        pay: {
            payBasis: ['hourly', 'per_shift', 'daily', 'weekly', 'monthly', 'piecework', 'unknown'].includes(payBasisValue) ? payBasisValue : 'unknown',
            amount: ['hourly', 'per_shift', 'daily', 'weekly', 'monthly'].includes(payBasisValue) ? payAmountValue : null
        }
    };

    if (workplaceValue === 'other' && workplaceOtherValue) {
        payload.workplaceOther = workplaceOtherValue;
    }

    return payload;
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
    documentsAvailableField.addEventListener('change', updateEmploymentTypeOnDocumentsVisibility);
}

if (workplaceField && typeof workplaceField.addEventListener === 'function') {
    workplaceField.addEventListener('change', updateWorkplaceVisibility);
}

if (payBasisField && typeof payBasisField.addEventListener === 'function') {
    payBasisField.addEventListener('change', updatePayBasisVisibility);
}

updateEmploymentTypeOnDocumentsVisibility();
updateWorkplaceVisibility();
updatePayBasisVisibility();

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