const choiceButtons = [...document.querySelectorAll('.choice')];
const error = document.getElementById('error');
const questionView = document.getElementById('question-view');
const resultView = document.getElementById('result-view');
const documentsAvailableField = document.getElementById('documentsAvailable');
const payslipStatusField = document.getElementById('payslipStatus');
const casualShownOnDocumentsField = document.getElementById('casualShownOnDocuments');
const casualQuestionGroup = casualShownOnDocumentsField?.closest('.field-group');

function updateCasualDocumentVisibility() {
    if (!documentsAvailableField || !casualShownOnDocumentsField || !casualQuestionGroup) {
        return;
    }

    const availability = documentsAvailableField.value;
    const payslipStatus = payslipStatusField?.value || '';
    const hasPayslip = ['yes', 'sometimes'].includes(payslipStatus);

    const shouldShowCasualQuestion = availability === 'yes'
        || availability === 'no_payslip'
        || (availability === 'no_contract' && hasPayslip);

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

    const documentAvailability = documentsAvailableValue === 'no_both' ? 'none' : (documentsAvailableValue || 'unknown');
    const casualShownOnDocuments = documentsAvailableValue === 'no_both' || documentsAvailableValue === 'unknown'
        ? 'unknown'
        : (casualValue || 'unknown');

    return {
        workplace: getTextValue('workplace'),
        employmentType: explicitEmploymentType || 'unknown',
        workTime: selectedWorkTimes,
        description: getTextValue('description'),
        overtime: getTextValue('overtime'),
        visaThreat: getTextValue('visaThreat'),
        documentAvailability,
        casualShownOnDocuments,
        employmentPattern: {
            workPattern,
            hoursPerWeek: getNumberValue('hoursPerWeek'),
            paidLeave: paidLeaveValue === 'yes' ? true : paidLeaveValue === 'no' ? false : null,
            documentAvailability,
            casualShownOnDocuments
        },
        pay: {
            hourlyPay: getNumberValue('hourlyPay'),
            hourlyPayConfirmed: hourlyPayConfirmedValue === 'yes' ? true : hourlyPayConfirmedValue === 'no' ? false : 'unknown',
            payslipStatus: payslipStatusValue || 'unknown',
            paymentMethod: paymentMethodValue || 'unknown'
        }
    };
}

if (documentsAvailableField) {
    documentsAvailableField.addEventListener('change', updateCasualDocumentVisibility);
}

if (payslipStatusField) {
    payslipStatusField.addEventListener('change', updateCasualDocumentVisibility);
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