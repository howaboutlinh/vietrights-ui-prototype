const choiceButtons = [...document.querySelectorAll('.choice')];
const error = document.getElementById('error');
const questionView = document.getElementById('question-view');
const resultView = document.getElementById('result-view');
const stepPanels = [...document.querySelectorAll('.step-panel')];
const summaryItems = [...document.querySelectorAll('.summary-item')];
const progressFill = document.getElementById('progressFill');
const stepStatusText = document.getElementById('stepStatusText');
const stepMetaText = document.getElementById('stepMetaText');
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
const languageToggleButton = document.querySelector('.language');

let currentLanguage = 'vi';
let currentStep = 1;

const translations = {
    vi: {
        navHowItWorks: 'Cách hoạt động',
        navSources: 'Nguồn đáng tin cậy',
        eyebrow: 'Kiểm tra quyền tại nơi làm việc',
        heroHeading: 'Hiểu tình huống của bạn, từng bước một.',
        intro: 'Không cần biết thuật ngữ pháp lý. VietRights sẽ hỏi những thông tin cần thiết và đưa ra hướng dẫn rõ ràng dựa trên nguồn chính thức.',
        privacyNote: 'Để bảo vệ quyền riêng tư, không nhập số hộ chiếu, visa, TFN hoặc thông tin ngân hàng.',
        mainIssueLabel: 'Vấn đề chính của bạn là gì?',
        selectPlaceholder: 'Chọn',
        mainIssuePay: 'Lương / trả lương không đúng',
        mainIssueHours: 'Giờ làm / làm thêm / nghỉ giữa ca',
        mainIssueDocs: 'Hợp đồng / payslip / giấy tờ',
        mainIssueVisa: 'Visa / đe dọa liên quan tới visa',
        mainIssueOther: 'Khác',
        progressStatus: 'Đang làm rõ tình huống',
        progressMeta: 'Đã thu thập 3/5 nhóm thông tin',
        workTimeLabel: 'Thời gian làm việc',
        workTimeHeading: 'Bạn thường làm việc vào thời điểm nào?',
        workTimeHelp: 'Có thể chọn nhiều đáp án.',
        workTimeWeekdayTitle: 'Ngày thường',
        workTimeWeekdaySubtitle: 'Thứ Hai đến Thứ Sáu',
        workTimeNightTitle: 'Buổi tối hoặc ban đêm',
        workTimeNightSubtitle: 'Ca làm ngoài giờ ban ngày thông thường',
        workTimeWeekendTitle: 'Cuối tuần',
        workTimeWeekendSubtitle: 'Thứ Bảy hoặc Chủ Nhật',
        workTimeHolidayTitle: 'Ngày lễ',
        workTimeHolidaySubtitle: 'Public holiday tại bang hoặc vùng của bạn',
        workTimeVariableTitle: 'Lịch thay đổi thường xuyên',
        workTimeVariableSubtitle: 'Không có lịch làm cố định mỗi tuần',
        workTimeUnknownTitle: 'Tôi không chắc',
        workTimeUnknownSubtitle: 'Bạn vẫn có thể tiếp tục kiểm tra',
        workplaceLabel: 'Bạn đang làm việc ở môi trường nào?',
        workplaceRestaurant: 'Nhà hàng / quán ăn',
        workplaceCafe: 'Cafe / takeaway',
        workplaceRetail: 'Bán lẻ / cửa hàng',
        workplaceFactory: 'Nhà máy / kho',
        workplaceCleaning: 'Vệ sinh',
        workplaceConstruction: 'Xây dựng',
        workplaceCare: 'Chăm sóc / aged care',
        workplaceOffice: 'Văn phòng',
        optionOther: 'Khác',
        optionUnknown: 'Không chắc',
        workplaceOtherLabel: 'Bạn có thể ghi rõ môi trường làm việc của mình',
        workplaceOtherPlaceholder: 'Ví dụ: tiệm nail, salon tóc, giao hàng, làm vườn...',
        payBasisLabel: 'Bạn được trả lương theo cách nào?',
        payAmountHourly: 'Bạn được trả bao nhiêu cho mỗi giờ làm việc?',
        payAmountPlaceholder: 'Ví dụ: 28.50',
        payPieceworkDescriptionLabel: 'Hãy mô tả ngắn cách tính lương theo sản phẩm / công việc của bạn.',
        payPieceworkDescriptionPlaceholder: 'Ví dụ: Tôi được trả theo số món ăn / số đơn hàng hoàn thành...',
        workPatternLabel: 'Bạn làm việc theo kiểu nào?',
        workPatternRegular: 'Giờ làm khá cố định mỗi tuần',
        workPatternVariable: 'Số giờ/ca làm thay đổi theo tuần',
        workPatternOnCall: 'Tôi chỉ được gọi khi có ca',
        workPatternFixedTerm: 'Hợp đồng của tôi có ngày kết thúc',
        hoursPerWeekLabel: 'Bạn thường làm khoảng bao nhiêu giờ mỗi tuần?',
        hoursPerWeekPlaceholder: 'Ví dụ: 25',
        hoursPerWeekStatusLabel: 'Bạn thường làm khoảng bao nhiêu giờ mỗi tuần?',
        optionYes: 'Tôi biết',
        optionNo: 'Không',
        optionUnknownInfo: 'Không biết',
        optionNotSure: 'Không chắc',
        optionNoInfo: 'Không có thông tin này',
        hoursPerShiftLabel: 'Nếu biết, mỗi ca bạn thường làm khoảng bao nhiêu giờ?',
        hoursPerShiftPlaceholder: 'Ví dụ: 8',
        paidLeaveLabel: 'Bạn có nhận nghỉ phép có lương hoặc nghỉ ốm có lương không?',
        documentsAvailableLabel: 'Bạn có hợp đồng hoặc payslip để kiểm tra không?',
        documentsNoContract: 'Không có hợp đồng',
        documentsNoPayslip: 'Không có payslip',
        documentsNoBoth: 'Không có cả hai',
        employmentTypeLabel: 'Nếu có hợp đồng hoặc payslip, trên đó ghi loại hình làm việc của bạn là gì?',
        employmentFullTime: 'Full-time / Toàn thời gian',
        employmentPartTime: 'Part-time / Bán thời gian',
        employmentCasual: 'Casual',
        employmentFixedTerm: 'Fixed-term / Hợp đồng có thời hạn',
        employmentOther: 'Loại khác',
        employmentNotStated: 'Không ghi',
        employmentUnknown: 'Tôi không biết / không hiểu',
        payslipStatusLabel: 'Bạn có nhận được payslip / phiếu lương không?',
        payslipUnknown: 'Không biết payslip là gì',
        paymentMethodLabel: 'Bạn thường được trả lương bằng cách nào?',
        paymentBankTransfer: 'Chuyển khoản ngân hàng',
        paymentCash: 'Tiền mặt',
        paymentBoth: 'Cả hai',
        paymentOther: 'Cách khác',
        overtimeStatusLabel: 'Bạn có thường làm thêm ngoài giờ hoặc ở lại sau ca không?',
        breakStatusLabel: 'Bạn có được nghỉ giữa ca không?',
        visaThreatLabel: 'Bạn có bị đe dọa về visa / thị thực không?',
        descriptionLabel: 'Hãy mô tả ngắn tình huống của bạn',
        descriptionPlaceholder: 'Ví dụ: Tôi thường phải ở lại sau ca nhưng không được trả thêm...',
        errorDefault: 'Vui lòng chọn ít nhất một thời điểm để tiếp tục.',
        backButton: '← Quay lại',
        continueButton: 'Tiếp tục  →',
        resultEyebrow: 'Hướng dẫn dành cho bạn',
        resultTitle: 'Kết quả kiểm tra',
        resultRiskLevelPrefix: '● Mức độ cần chú ý:',
        resultIssuesHeading: 'Vấn đề cần xem xét',
        resultEvidenceHeading: 'Bằng chứng nên giữ',
        resultNextStepsHeading: 'Việc nên làm tiếp',
        editButton: '← Sửa câu trả lời',
        officialSourcesButton: 'Xem nguồn chính thức  →',
        casePanelTitle: 'Hồ sơ tình huống',
        casePanelIntro: 'VietRights chỉ hỏi những thông tin cần thiết để hiểu vấn đề của bạn.',
        summaryMainIssueTitle: 'Vấn đề chính',
        summaryPending: 'Chưa nhập',
        summaryWorkInfoTitle: 'Thông tin công việc',
        summaryWorkTimeTitle: 'Thời gian làm việc',
        summaryAnswering: 'Đang trả lời',
        summaryRiskTitle: 'Mức độ rủi ro',
        summaryNotAssessed: 'Chưa đánh giá',
        summaryGuidanceTitle: 'Hướng dẫn',
        summaryGuidanceSubtitle: 'Nguồn và bước tiếp theo',
        panelFooter: '🔒 Câu trả lời trong bản prototype này không được lưu lại.',
        optionSometimes: 'Đôi khi',
        workPatternUnknown: 'Tôi không chắc',
        resultSources: 'Nguồn:'
    },
    en: {
        navHowItWorks: 'How it works',
        navSources: 'Trustworthy sources',
        eyebrow: 'Workplace rights check',
        heroHeading: 'Understand your situation, step by step.',
        intro: 'You do not need to know the legal terms. VietRights will ask for the information needed and give clear guidance using official sources.',
        privacyNote: 'To protect your privacy, do not enter passport, visa, TFN, or bank details.',
        mainIssueLabel: 'What is your main issue?',
        selectPlaceholder: 'Select',
        mainIssuePay: 'Wages / incorrect pay',
        mainIssueHours: 'Hours / overtime / breaks',
        mainIssueDocs: 'Contracts / payslips / documents',
        mainIssueVisa: 'Visa / visa-related threats',
        mainIssueOther: 'Other',
        progressStatus: 'Clarifying the situation',
        progressMeta: 'Collected 3/5 information groups',
        workTimeLabel: 'Working times',
        workTimeHeading: 'When do you usually work?',
        workTimeHelp: 'You can select more than one answer.',
        workTimeWeekdayTitle: 'Weekdays',
        workTimeWeekdaySubtitle: 'Monday to Friday',
        workTimeNightTitle: 'Evening or night shift',
        workTimeNightSubtitle: 'Working outside normal daytime hours',
        workTimeWeekendTitle: 'Weekend',
        workTimeWeekendSubtitle: 'Saturday or Sunday',
        workTimeHolidayTitle: 'Public holiday',
        workTimeHolidaySubtitle: 'Public holiday in your state or region',
        workTimeVariableTitle: 'Variable schedule',
        workTimeVariableSubtitle: 'No fixed weekly routine',
        workTimeUnknownTitle: 'Not sure',
        workTimeUnknownSubtitle: 'You can still continue checking',
        workplaceLabel: 'What kind of workplace are you in?',
        workplaceRestaurant: 'Restaurant / café',
        workplaceCafe: 'Cafe / takeaway',
        workplaceRetail: 'Retail / shop',
        workplaceFactory: 'Factory / warehouse',
        workplaceCleaning: 'Cleaning',
        workplaceConstruction: 'Construction',
        workplaceCare: 'Care / aged care',
        workplaceOffice: 'Office',
        optionOther: 'Other',
        optionUnknown: 'Not sure',
        workplaceOtherLabel: 'You can describe your workplace in more detail',
        workplaceOtherPlaceholder: 'Example: nail salon, hair salon, delivery, gardening...',
        payBasisLabel: 'How are you paid?',
        payAmountHourly: 'How much are you paid for each hour worked?',
        payAmountPlaceholder: 'Example: 28.50',
        payPieceworkDescriptionLabel: 'Briefly describe how your piecework or task-based pay is calculated.',
        payPieceworkDescriptionPlaceholder: 'Example: I am paid per meal or completed order...',
        workPatternLabel: 'What kind of work pattern do you have?',
        workPatternRegular: 'Fairly regular weekly hours',
        workPatternVariable: 'Hours or shifts vary each week',
        workPatternOnCall: 'I am only called when there is a shift',
        workPatternFixedTerm: 'My contract has an end date',
        hoursPerWeekLabel: 'How many hours do you usually work each week?',
        hoursPerWeekPlaceholder: 'Example: 25',
        hoursPerWeekStatusLabel: 'How many hours do you usually work each week?',
        optionYes: 'I know',
        optionNo: 'No',
        optionUnknownInfo: 'Do not know',
        optionNotSure: 'Not sure',
        optionNoInfo: 'No information',
        hoursPerShiftLabel: 'If you know it, how many hours is each shift usually?',
        hoursPerShiftPlaceholder: 'Example: 8',
        paidLeaveLabel: 'Do you receive paid leave or paid sick leave?',
        documentsAvailableLabel: 'Do you have a contract or payslip to check?',
        documentsNoContract: 'No contract',
        documentsNoPayslip: 'No payslip',
        documentsNoBoth: 'Neither',
        employmentTypeLabel: 'If you have a contract or payslip, what employment type is listed?',
        employmentFullTime: 'Full-time',
        employmentPartTime: 'Part-time',
        employmentCasual: 'Casual',
        employmentFixedTerm: 'Fixed-term',
        employmentOther: 'Other type',
        employmentNotStated: 'Not stated',
        employmentUnknown: 'I do not know / I do not understand',
        payslipStatusLabel: 'Do you receive a payslip?',
        payslipUnknown: 'I do not know what a payslip is',
        paymentMethodLabel: 'How are you usually paid?',
        paymentBankTransfer: 'Bank transfer',
        paymentCash: 'Cash',
        paymentBoth: 'Both',
        paymentOther: 'Other method',
        overtimeStatusLabel: 'Do you often work overtime or stay after a shift?',
        breakStatusLabel: 'Do you get a break between shifts?',
        visaThreatLabel: 'Are you being threatened because of your visa?',
        descriptionLabel: 'Briefly describe your situation',
        descriptionPlaceholder: 'Example: I often have to stay back after a shift but am not paid extra...',
        errorDefault: 'Please choose at least one work time option to continue.',
        backButton: '← Back',
        continueButton: 'Continue  →',
        resultEyebrow: 'Guidance for you',
        resultTitle: 'Check result',
        resultRiskLevelPrefix: '● Risk level:',
        resultIssuesHeading: 'Issues to review',
        resultEvidenceHeading: 'Documents to keep',
        resultNextStepsHeading: 'Next steps',
        editButton: '← Edit answers',
        officialSourcesButton: 'View official sources  →',
        casePanelTitle: 'Situation summary',
        casePanelIntro: 'VietRights only asks for the information needed to understand your situation.',
        summaryMainIssueTitle: 'Main issue',
        summaryPending: 'Not entered',
        summaryWorkInfoTitle: 'Job information',
        summaryWorkTimeTitle: 'Work times',
        summaryAnswering: 'In progress',
        summaryRiskTitle: 'Risk level',
        summaryNotAssessed: 'Not assessed',
        summaryGuidanceTitle: 'Guidance',
        summaryGuidanceSubtitle: 'Sources and next steps',
        panelFooter: '🔒 Responses in this prototype are not stored.',
        optionSometimes: 'Sometimes',
        workPatternUnknown: 'Not sure',
        resultSources: 'Source:'
    }
};

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

function getWeeklyHoursState() {
    const directInput = document.getElementById('hoursPerWeekInput');
    const legacyInput = document.getElementById('hoursPerWeek');
    const knownField = document.getElementById('hoursPerWeekKnown');
    const inputValue = (directInput ? directInput.value : '') || (legacyInput ? legacyInput.value : '');
    const knownValue = knownField ? knownField.value : '';

    if (knownValue === 'false') {
        return { hoursPerWeek: null, hoursPerWeekKnown: false };
    }

    if (inputValue !== '') {
        const parsed = Number(inputValue);
        if (Number.isFinite(parsed) && parsed >= 0) {
            return { hoursPerWeek: parsed, hoursPerWeekKnown: true };
        }
    }

    return { hoursPerWeek: null, hoursPerWeekKnown: false };
}

function updateProgressState() {
    const progressMap = {
        1: 20,
        2: 40,
        3: 60,
        4: 80,
        5: 100
    };

    const stepLabels = {
        1: 'Bước 1 · Vấn đề chính',
        2: 'Bước 2 · Thông tin công việc',
        3: 'Bước 3 · Thời gian làm việc',
        4: 'Bước 4 · Mức độ rủi ro',
        5: 'Bước 5 · Hướng dẫn'
    };

    const nextPercent = progressMap[currentStep] ?? 20;
    if (progressFill) {
        progressFill.style.width = `${nextPercent}%`;
    }
    if (stepStatusText) {
        stepStatusText.textContent = stepLabels[currentStep] || 'Đang làm rõ tình huống';
    }
    if (stepMetaText) {
        stepMetaText.textContent = `Bước ${currentStep} / 5`;
    }

    summaryItems.forEach((item, index) => {
        const stepNumber = index + 1;
        item.classList.remove('done', 'current', 'upcoming');

        if (currentStep === 5 && stepNumber === 5) {
            item.classList.add('current');
        } else if (stepNumber < currentStep) {
            item.classList.add('done');
        } else if (stepNumber === currentStep) {
            item.classList.add('current');
        } else {
            item.classList.add('upcoming');
        }

        const dot = item.querySelector('.dot');
        if (dot) {
            dot.textContent = stepNumber;
        }
    });
}

function showStep(step) {
    currentStep = Math.min(4, Math.max(1, Number(step) || 1));
    stepPanels.forEach((panel) => {
        const isVisible = Number(panel.dataset.step) === currentStep;
        panel.classList.toggle('active', isVisible);
        panel.style.display = isVisible ? 'block' : 'none';
    });
    updateProgressState();
    questionView.style.display = 'block';
    resultView.style.display = 'none';
    clearFieldErrors();
}

function applyTranslations() {
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach((element) => {
        const key = element.getAttribute('data-i18n');
        const text = translations[currentLanguage]?.[key];
        if (text) {
            element.textContent = text;
        }
    });

    const placeholderTargets = document.querySelectorAll('[data-i18n-placeholder]');
    placeholderTargets.forEach((element) => {
        const key = element.getAttribute('data-i18n-placeholder');
        const placeholder = translations[currentLanguage]?.[key];
        if (placeholder) {
            element.setAttribute('placeholder', placeholder);
        }
    });

    const toggles = document.querySelectorAll('.lang-segment');
    toggles.forEach((segment) => {
        const isActive = segment.getAttribute('data-lang-segment') === currentLanguage;
        segment.style.fontWeight = isActive ? '700' : '400';
        segment.style.opacity = isActive ? '1' : '0.7';
    });

    const languageButton = document.querySelector('.language');
    if (languageButton) {
        languageButton.setAttribute('aria-pressed', String(currentLanguage === 'en'));
    }
}

function setLanguage(language) {
    currentLanguage = language === 'en' ? 'en' : 'vi';
    applyTranslations();
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

function validateCurrentStep() {
    clearFieldErrors();

    if (currentStep === 1) {
        if (!mainIssueField || !mainIssueField.value) {
            showFieldError('mainIssueError', 'Vui lòng chọn vấn đề chính của bạn.');
            return false;
        }
        return true;
    }

    if (currentStep === 2) {
        const workplaceValue = document.getElementById('workplace')?.value || '';
        const workplaceOtherValue = document.getElementById('workplaceOther')?.value || '';
        const workPatternValue = document.getElementById('workPattern')?.value || '';
        const payBasisValue = document.getElementById('payBasis')?.value || '';
        const payAmountValue = document.getElementById('payAmount')?.value || '';
        const payPieceworkDescriptionValue = document.getElementById('payPieceworkDescription')?.value || '';

        if (!workplaceValue) {
            showFieldError('workplaceError', 'Vui lòng chọn môi trường làm việc.');
            return false;
        }
        if (workplaceValue === 'other' && !fieldIsAnswered(workplaceOtherValue)) {
            showFieldError('workplaceOtherError', 'Vui lòng ghi rõ môi trường làm việc của bạn.');
            return false;
        }
        if (!workPatternValue) {
            showFieldError('workPatternError', 'Vui lòng chọn kiểu làm việc.');
            return false;
        }
        if (!payBasisValue) {
            showFieldError('payBasisError', 'Vui lòng chọn cách bạn được trả lương.');
            return false;
        }
        if (['hourly', 'per_shift', 'daily', 'weekly', 'monthly'].includes(payBasisValue) && !fieldIsAnswered(payAmountValue)) {
            showFieldError('payAmountError', 'Vui lòng nhập số tiền phù hợp với cách trả lương bạn đã chọn.');
            return false;
        }
        if (payBasisValue === 'piecework' && !fieldIsAnswered(payPieceworkDescriptionValue)) {
            showFieldError('payPieceworkDescriptionError', 'Vui lòng mô tả ngắn cách tính lương theo sản phẩm hoặc công việc.');
            return false;
        }
        return true;
    }

    if (currentStep === 3) {
        if (!hasSelectedWorkTime()) {
            showFieldError('workTimeError', 'Vui lòng chọn ít nhất một thời điểm làm việc.');
            return false;
        }
        return true;
    }

    if (currentStep === 4) {
        return validateContextualFields();
    }

    return true;
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
    const hoursPerWeekValue = document.getElementById('hoursPerWeekInput')?.value || document.getElementById('hoursPerWeek')?.value || '';
    const { hoursPerWeek: resolvedHoursPerWeek, hoursPerWeekKnown } = getWeeklyHoursState();
    const payBasisValue = document.getElementById('payBasis')?.value || '';
    const payAmountValue = document.getElementById('payAmount')?.value || '';
    const payPieceworkDescriptionValue = document.getElementById('payPieceworkDescription')?.value || '';
    const payslipStatusValue = document.getElementById('payslipStatus')?.value || '';

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
        const hasHoursPerWeek = resolvedHoursPerWeek !== null || hoursPerWeekKnown === false;

        if (!hasHoursPerWeek) {
            showFieldError('hoursPerWeekStatusError', 'Vui lòng nhập số giờ làm mỗi tuần hoặc chọn “Tôi không chắc”.');
            valid = false;
        }

        if (!payslipStatusValue) {
            showFieldError('payslipStatusError', 'Vui lòng cho biết bạn có nhận payslip không.');
            valid = false;
        }
    }

    if (isHoursIssue) {
        const hasHoursPerWeek = resolvedHoursPerWeek !== null || hoursPerWeekKnown === false;

        if (!hasHoursPerWeek) {
            showFieldError('hoursPerWeekStatusError', 'Vui lòng nhập số giờ làm mỗi tuần hoặc chọn “Tôi không chắc”.');
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
        const hasWeekInfo = resolvedHoursPerWeek !== null || hoursPerWeekKnown === false;
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
    const { hoursPerWeek, hoursPerWeekKnown } = getWeeklyHoursState();

    const documentAvailability = documentsAvailableValue === 'no_both' ? 'none' : (documentsAvailableValue || 'unknown');
    const shouldShowEmploymentTypeQuestion = ['yes', 'no_contract', 'no_payslip'].includes(documentsAvailableValue || '');
    const employmentTypeOnDocuments = shouldShowEmploymentTypeQuestion ? (employmentTypeOnDocumentsValue || 'unknown') : 'unknown';

    const payload = {
        mainIssue,
        language: currentLanguage,
        workplace: workplaceValue === 'other' && workplaceOtherValue ? 'other' : (workplaceValue || 'unknown'),
        workTime: selectedWorkTimes,
        description: getTextValue('description'),
        overtimeStatus: overtimeStatusValue || 'unknown',
        breakStatus: breakStatusValue || 'unknown',
        hoursPerWeek: hoursPerWeek,
        hoursPerWeekKnown: hoursPerWeekKnown,
        hoursPerShift: getNumberValue('hoursPerShift'),
        visaThreat: getTextValue('visaThreat'),
        documentAvailability,
        employmentTypeOnDocuments,
        employmentPattern: {
            workPattern,
            hoursPerWeek: hoursPerWeek,
            hoursPerWeekKnown: hoursPerWeekKnown,
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

if (languageToggleButton && typeof languageToggleButton.addEventListener === 'function') {
    languageToggleButton.addEventListener('click', () => {
        setLanguage(currentLanguage === 'vi' ? 'en' : 'vi');
    });
}

updateEmploymentTypeOnDocumentsVisibility();
updateWorkplaceVisibility();
updatePayBasisVisibility();
applyTranslations();
updateProgressState();
showStep(1);

choiceButtons.forEach((button) => {
    button.addEventListener('click', () => {
        const selected = button.getAttribute('aria-pressed') === 'true';
        button.setAttribute('aria-pressed', String(!selected));
        const activeError = document.getElementById('workTimeError') || error;
        if (activeError) {
            activeError.style.display = 'none';
        }
    });
});

document.querySelectorAll('.step-next').forEach((button) => {
    button.addEventListener('click', async () => {
        clearFieldErrors();

        if (!validateCurrentStep()) {
            if (error) {
                error.style.display = 'none';
            }
            window.scrollTo({ top: 0, behavior: 'smooth' });
            return;
        }

        if (currentStep < 4) {
            showStep(currentStep + 1);
            return;
        }

        try {
            const submitButton = button;
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Đang phân tích...';

            const result = await sendCaseToBackend();
            console.log("Analysis result:", result);

            renderResult(result);
            questionView.style.display = 'none';
            resultView.style.display = 'block';
            currentStep = 5;
            updateProgressState();

            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
            submitButton.textContent = originalText;
            submitButton.disabled = false;
        } catch (error) {
            console.error("Failed to analyze case:", error);
            button.disabled = false;
            button.textContent = 'Phân tích tình huống';
        }
    });
});

document.querySelectorAll('.step-back').forEach((button) => {
    button.addEventListener('click', () => {
        if (currentStep > 1) {
            showStep(currentStep - 1);
        }
    });
});

document.getElementById('edit').addEventListener('click', () => {
    resultView.style.display = 'none';
    questionView.style.display = 'block';
    currentStep = 1;
    showStep(1);
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