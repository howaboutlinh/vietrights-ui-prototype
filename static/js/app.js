const choiceButtons = [...document.querySelectorAll('.choice')];
const error = document.getElementById('error');
const questionView = document.getElementById('question-view');
const resultView = document.getElementById('result-view');

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
    const casualValue = getTextValue('casualShownOnDocuments');

    return {
        workplace: getTextValue('workplace'),
        employmentType: explicitEmploymentType || 'unknown',
        hourlyPay: getNumberValue('hourlyPay'),
        receivesPayslip: getTextValue('receivesPayslip'),
        paidCash: getTextValue('paidCash'),
        overtime: getTextValue('overtime'),
        visaThreat: getTextValue('visaThreat'),
        workTime: selectedWorkTimes,
        description: getTextValue('description'),
        employmentPattern: {
            workPattern,
            hoursPerWeek: getNumberValue('hoursPerWeek'),
            paidLeave: paidLeaveValue === 'yes' ? true : paidLeaveValue === 'no' ? false : null,
            casualShownOnDocuments: casualValue || 'unknown'
        }
    };
}

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