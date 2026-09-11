const choiceButtons = [...document.querySelectorAll('.choice')];
const error = document.getElementById('error');
const questionView = document.getElementById('question-view');
const resultView = document.getElementById('result-view');

function collectCaseData() {
    const summaryEntries = [...document.querySelectorAll('.summary-item .summary-copy')].reduce((acc, item) => {
        const label = item.querySelector('strong')?.textContent?.trim();
        const value = item.querySelector('span')?.textContent?.trim();

        if (label && value) {
            acc[label] = value;
        }

        return acc;
    }, {});

    const selectedWorkTimes = [...document.querySelectorAll('.choice[aria-pressed="true"]')]
        .map((button) => button.querySelector('strong')?.textContent?.trim())
        .filter(Boolean);

    const workInfo = (summaryEntries['Thông tin công việc'] || '').split('·').map((item) => item.trim()).filter(Boolean);
    const riskLevel = document.querySelector('.result-tag')?.textContent?.replace(/^●\s*Mức độ cần chú ý:\s*/i, '').trim() || null;

    const getTextFieldValue = (id) => {
        const field = document.getElementById(id);
        if (!field) return null;
        const value = field.value?.trim();
        return value ? value : null;
    };

    const issue = summaryEntries['Vấn đề chính'] || null;
    const workplace = workInfo[0] || null;
    const employmentType = getTextFieldValue('employmentType') || workInfo[1] || null;

    return {
        issue,
        workplace,
        hourlyPay: getTextFieldValue('hourlyPay'),
        employmentType,
        receivesPayslip: getTextFieldValue('receivesPayslip'),
        paidCash: getTextFieldValue('paidCash'),
        hoursWorked: getTextFieldValue('hoursWorked'),
        overtime: getTextFieldValue('overtime'),
        visaThreat: getTextFieldValue('visaThreat'),
        description: getTextFieldValue('description'),
        workTime: selectedWorkTimes,
        riskLevel
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