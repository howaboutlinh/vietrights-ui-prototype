const choiceButtons = [...document.querySelectorAll('.choice')];
const error = document.getElementById('error');
const questionView = document.getElementById('question-view');
const resultView = document.getElementById('result-view');
const documentsAvailableField = document.getElementById('documentsAvailable');
const casualShownOnDocumentsField = document.getElementById('casualShownOnDocuments');
const casualQuestionGroup = casualShownOnDocumentsField && (
    casualShownOnDocumentsField.closest ? casualShownOnDocumentsField.closest('.field-group') : casualShownOnDocumentsField.parentElement
);

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
    const hasSelection = choiceButtons.some(
        (button) => button.getAttribute('aria-pressed') === 'true'
    );

    if (!hasSelection) {
        error.style.display = 'block';
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