const stepLabels = {
  1: { vi: 'Bước 1 · Vấn đề chính', en: 'Step 1 · Main issue' },
  2: { vi: 'Bước 2 · Thông tin công việc', en: 'Step 2 · Job details' },
  3: { vi: 'Bước 3 · Thời gian làm việc', en: 'Step 3 · Work schedule' },
  4: { vi: 'Bước 4 · Mức độ rủi ro', en: 'Step 4 · Risk check' },
  5: { vi: 'Bước 5 · Hướng dẫn', en: 'Step 5 · Guidance' }
};

const translations = {
  vi: {
    nav_home: 'Trang chủ',
    nav_how: 'Cách hoạt động',
    nav_sources: 'Nguồn đáng tin cậy',
    nav_about: 'Về dự án',
    nav_cta: 'Bắt đầu ngay',
    hero_eyebrow: 'KIẾN THỨC. QUYỀN LỢI. MỘT CỘNG ĐỒNG MẠNH HƠN.',
    hero_title: 'Bạn không\nđơn độc.',
    hero_desc: 'VietRights giúp người lao động Việt Nam tại Úc hiểu rõ quyền lợi của mình, tìm câu trả lời đáng tin cậy và biết nên làm gì tiếp theo — bằng tiếng Việt, dễ hiểu và dựa trên nguồn chính thức.',
    hero_cta: 'Kiểm tra tình huống của bạn',
    hero_secondary: 'Tìm hiểu thêm',
    about_eyebrow: 'VỀ VIETRIGHTS',
    about_title: 'Quyền lợi của bạn\nlà điều quan trọng.',
    about_desc: 'VietRights được tạo ra để hỗ trợ người lao động Việt Nam tại Úc — đặc biệt là những người gặp khó khăn về ngôn ngữ hoặc chưa quen với luật lao động. Hệ thống kết hợp AI với các nguồn chính thức để cung cấp thông tin dễ hiểu, có căn cứ và phù hợp với tình huống của bạn.',
    feature_1: 'Giải thích quyền lợi rõ ràng, dễ hiểu',
    feature_2: 'Gợi ý bước tiếp theo thực tế',
    feature_3: 'Kết nối với hỗ trợ phù hợp',
    trust_vi: 'Dễ hiểu\nbằng tiếng Việt',
    trust_sources: 'Dựa trên nguồn\nchính thức',
    trust_private: 'Ẩn danh\nvà an toàn',
    source_intro: 'Dựa trên thông tin từ các nguồn đáng tin cậy'
  },
  en: {
    nav_home: 'Home',
    nav_how: 'How it works',
    nav_sources: 'Reliable sources',
    nav_about: 'About',
    nav_cta: 'Start now',
    hero_eyebrow: 'KNOWLEDGE. RIGHTS. A STRONGER COMMUNITY.',
    hero_title: 'You are not\nalone.',
    hero_desc: 'VietRights helps Vietnamese workers in Australia understand their rights, find trustworthy answers, and know what to do next — in plain Vietnamese and grounded in official sources.',
    hero_cta: 'Check your situation',
    hero_secondary: 'Learn more',
    about_eyebrow: 'ABOUT VIETRIGHTS',
    about_title: 'Your rights\nmatter.',
    about_desc: 'VietRights was created to support Vietnamese workers in Australia — especially those who face language barriers or are unfamiliar with workplace laws. The system combines AI with official sources to provide clear, evidence-based guidance tailored to your situation.',
    feature_1: 'Clear and easy-to-understand rights guidance',
    feature_2: 'Practical next-step suggestions',
    feature_3: 'Links to the right support',
    trust_vi: 'Easy to understand\nin Vietnamese',
    trust_sources: 'Based on official\nsources',
    trust_private: 'Private\nand safe',
    source_intro: 'Based on information from trusted sources'
  }
};

let currentLanguage = 'vi';
let currentStep = 1;

const requiredStepFieldIds = {
  1: ['main-issue'],
  2: ['workplace', 'work-pattern', 'paid-leave', 'documents', 'pay-basis', 'payslip-status', 'payment-method'],
  3: ['hours-per-week', 'overtime', 'breaks'],
  4: ['visa-threat', 'immediate-danger', 'safety-concern', 'coercion']
};

function clearFieldErrors() {
  document.querySelectorAll('.field-error').forEach((node) => {
    node.textContent = '';
    node.style.display = 'none';
  });
}

function showFieldError(fieldId, message) {
  const target = document.querySelector(`[data-error-for="${fieldId}"]`) || document.getElementById(fieldId);
  if (!target) return;
  if (target.dataset && target.dataset.errorFor) {
    target.textContent = message;
    target.style.display = 'block';
    return;
  }
  target.setCustomValidity(message);
  target.reportValidity?.();
}

function updateConditionalFields() {
  const mainIssue = document.getElementById('main-issue');
  const mainIssueOtherWrap = document.getElementById('main-issue-other-wrap');
  if (mainIssue && mainIssueOtherWrap) {
    const shouldShow = mainIssue.value === 'other';
    mainIssueOtherWrap.hidden = !shouldShow;
    if (!shouldShow) {
      const mainIssueOther = document.getElementById('main-issue-other');
      if (mainIssueOther) mainIssueOther.value = '';
    }
  }

  const workplace = document.getElementById('workplace');
  const workplaceOtherWrap = document.getElementById('workplace-other-wrap');
  if (workplace && workplaceOtherWrap) {
    const shouldShow = workplace.value === 'other';
    workplaceOtherWrap.hidden = !shouldShow;
    if (!shouldShow) {
      const workplaceOther = document.getElementById('workplace-other');
      if (workplaceOther) workplaceOther.value = '';
    }
  }

  const documents = document.getElementById('documents');
  const employmentDocWrap = document.getElementById('employment-doc-wrap');
  const employmentDocType = document.getElementById('employment-doc-type');
  if (documents && employmentDocWrap && employmentDocType) {
    const shouldShow = ['both', 'no_contract', 'no_payslip'].includes((documents.value || '').trim());
    employmentDocWrap.hidden = !shouldShow;
    if (!shouldShow) {
      employmentDocType.value = 'unknown';
    } else if (!employmentDocType.value) {
      employmentDocType.value = 'unknown';
    }
  }

  const payBasis = document.getElementById('pay-basis');
  const payAmountWrap = document.getElementById('pay-amount-wrap');
  const pieceworkWrap = document.getElementById('piecework-wrap');
  const payAmount = document.getElementById('pay-amount');
  const pieceworkDescription = document.getElementById('piecework-description');
  const payAmountLabel = document.getElementById('pay-amount-label');

  if (payBasis && payAmountWrap && pieceworkWrap && payAmountLabel) {
    const value = payBasis.value;
    const labels = {
      hourly: 'Bạn được trả bao nhiêu mỗi giờ?',
      per_shift: 'Bạn được trả bao nhiêu cho mỗi ca?',
      daily: 'Bạn được trả bao nhiêu cho mỗi ngày?',
      weekly: 'Bạn được trả bao nhiêu cho mỗi tuần?',
      monthly: 'Bạn được trả bao nhiêu cho mỗi tháng?'
    };

    if (value && labels[value]) {
      payAmountLabel.textContent = labels[value];
      payAmountWrap.hidden = false;
      pieceworkWrap.hidden = true;
      if (pieceworkDescription) pieceworkDescription.value = '';
    } else if (value === 'piecework') {
      payAmountWrap.hidden = true;
      pieceworkWrap.hidden = false;
      if (payAmount) payAmount.value = '';
    } else {
      payAmountWrap.hidden = true;
      pieceworkWrap.hidden = true;
      if (payAmount) payAmount.value = '';
      if (pieceworkDescription) pieceworkDescription.value = '';
    }
  }
}

function setLanguage(language) {
  currentLanguage = language === 'en' ? 'en' : 'vi';
  applyTranslations();
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach((node) => {
    const key = node.getAttribute('data-i18n');
    const value = translations[currentLanguage]?.[key];
    if (value) {
      node.textContent = value;
    }
  });

  const languageToggle = document.getElementById('language-toggle');
  if (languageToggle) {
    languageToggle.textContent = currentLanguage === 'vi' ? 'VI / EN' : 'EN / VI';
  }

  const stepLabel = document.getElementById('step-label');
  if (stepLabel) {
    stepLabel.textContent = stepLabels[currentStep]?.[currentLanguage] || stepLabels[1].vi;
  }

  const continueBtn = document.getElementById('continue-btn');
  if (continueBtn) {
    continueBtn.textContent = currentStep === 4 ? (currentLanguage === 'en' ? 'Analyze case →' : 'Phân tích tình huống →') : (currentLanguage === 'en' ? 'Continue →' : 'Tiếp tục →');
  }

  const backBtn = document.getElementById('back-btn');
  if (backBtn && !backBtn.hidden) {
    backBtn.textContent = currentLanguage === 'en' ? '← Back' : '← Quay lại';
  }
}

function updateProgressUI() {
  const progressFill = document.getElementById('progress-fill');
  const stepLabel = document.getElementById('step-label');
  const stepCount = document.getElementById('step-count');
  const backBtn = document.getElementById('back-btn');
  const continueBtn = document.getElementById('continue-btn');

  const progressMap = { 1: 20, 2: 40, 3: 60, 4: 80, 5: 100 };
  if (progressFill) progressFill.style.width = `${progressMap[currentStep] || 20}%`;
  if (stepLabel) stepLabel.textContent = stepLabels[currentStep]?.[currentLanguage] || stepLabels[1].vi;
  if (stepCount) stepCount.textContent = `${currentLanguage === 'en' ? 'Step' : 'Bước'} ${currentStep} / 5`;
  if (backBtn) backBtn.hidden = currentStep === 1;
  if (continueBtn) {
    continueBtn.hidden = currentStep === 5;
    continueBtn.textContent = currentStep === 4
      ? (currentLanguage === 'en' ? 'Analyze case →' : 'Phân tích tình huống →')
      : (currentLanguage === 'en' ? 'Continue →' : 'Tiếp tục →');
  }

  document.querySelectorAll('.step-item').forEach((item) => {
    const itemStep = Number(item.dataset.sideStep);
    item.classList.toggle('is-active', itemStep === currentStep);
    item.classList.toggle('is-done', itemStep < currentStep);
  });
}

function showStep(step) {
  const nextStep = Math.min(5, Math.max(1, Number(step) || 1));
  currentStep = nextStep;

  document.querySelectorAll('.form-step').forEach((panel) => {
    const isVisible = Number(panel.dataset.step) === nextStep;
    panel.hidden = !isVisible;
    panel.classList.toggle('is-active', isVisible);
  });

  updateProgressUI();
  clearFieldErrors();
}

function bindChoiceButtons() {
  document.querySelectorAll('.choice').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.classList.contains('is-selected')));
    button.addEventListener('click', () => {
      button.classList.toggle('is-selected');
      button.setAttribute('aria-pressed', String(button.classList.contains('is-selected')));
    });
  });
}

function valueOf(id) {
  const field = document.getElementById(id);
  if (!field) return '';
  return String(field.value || '').trim();
}

function getSelectedWorkTimes() {
  return [...document.querySelectorAll('.choice.is-selected')]
    .map((button) => button.dataset.value)
    .filter(Boolean);
}

function validateStep(step) {
  clearFieldErrors();

  if (step === 1) {
    const field = document.getElementById('main-issue');
    if (!field || !field.value) {
      showFieldError('main-issue', 'Vui lòng chọn vấn đề chính của bạn.');
      return false;
    }
    if (field.value === 'other') {
      const otherField = document.getElementById('main-issue-other');
      if (!otherField || !otherField.value.trim()) {
        showFieldError('main-issue', 'Vui lòng mô tả rõ vấn đề của bạn.');
        return false;
      }
    }
    return true;
  }

  if (step === 2) {
    const workplace = valueOf('workplace');
    const workplaceOther = valueOf('workplace-other');
    const workPattern = valueOf('work-pattern');
    const paidLeave = valueOf('paid-leave');
    const documents = valueOf('documents');
    const employmentDoc = valueOf('employment-doc-type');
    const payBasis = valueOf('pay-basis');
    const payAmount = valueOf('pay-amount');
    const pieceworkDescription = valueOf('piecework-description');
    const payslipStatus = valueOf('payslip-status');
    const paymentMethod = valueOf('payment-method');

    if (!workplace) { showFieldError('workplace', 'Vui lòng chọn môi trường làm việc.'); return false; }
    if (workplace === 'other' && !workplaceOther) { showFieldError('workplace', 'Vui lòng ghi rõ môi trường làm việc của bạn.'); return false; }
    if (!workPattern) { showFieldError('work-pattern', 'Vui lòng chọn kiểu làm việc.'); return false; }
    if (!paidLeave) { showFieldError('paid-leave', 'Vui lòng cho biết tình trạng nghỉ phép có lương.'); return false; }
    if (!documents) { showFieldError('documents', 'Vui lòng cho biết bạn có hợp đồng hoặc payslip không.'); return false; }
    const shouldRequireEmploymentDoc = ['both', 'no_contract', 'no_payslip'].includes(documents);
    if (shouldRequireEmploymentDoc && !employmentDoc) {
      showFieldError('employment-doc-type', 'Vui lòng cho biết loại hình làm việc trên giấy tờ.');
      return false;
    }
    if (!payBasis) { showFieldError('pay-basis', 'Vui lòng chọn cách bạn được trả lương.'); return false; }
    if (['hourly', 'per_shift', 'daily', 'weekly', 'monthly'].includes(payBasis) && !payAmount) {
      showFieldError('pay-amount', 'Vui lòng nhập số tiền phù hợp với cách trả lương đã chọn.');
      return false;
    }
    if (payBasis === 'piecework' && !pieceworkDescription) {
      showFieldError('piecework-description', 'Vui lòng mô tả cách bạn được tính lương.');
      return false;
    }
    if (!payslipStatus) { showFieldError('payslip-status', 'Vui lòng cho biết bạn có nhận được payslip không.'); return false; }
    if (!paymentMethod) { showFieldError('payment-method', 'Vui lòng cho biết cách bạn thường được trả tiền.'); return false; }
    return true;
  }

  if (step === 3) {
    const hasWorkTimes = getSelectedWorkTimes().length > 0;
    const hoursUnknown = document.getElementById('hours-unknown')?.checked;
    const hoursPerWeek = valueOf('hours-per-week');
    const overtime = valueOf('overtime');
    const breaks = valueOf('breaks');

    if (!hasWorkTimes) {
      showFieldError('work-time', 'Vui lòng chọn ít nhất một thời điểm làm việc.');
      return false;
    }
    if (!hoursUnknown && !hoursPerWeek) {
      showFieldError('hours-per-week', 'Vui lòng nhập số giờ mỗi tuần hoặc chọn “Tôi không chắc”.');
      return false;
    }
    if (!overtime) { showFieldError('overtime', 'Vui lòng cho biết bạn có làm thêm giờ không.'); return false; }
    if (!breaks) { showFieldError('breaks', 'Vui lòng cho biết bạn có được nghỉ giữa ca không.'); return false; }
    return true;
  }

  if (step === 4) {
    for (const id of ['visa-threat', 'immediate-danger', 'safety-concern', 'coercion']) {
      if (!valueOf(id)) {
        showFieldError(id, 'Vui lòng chọn một đáp án cho câu hỏi này.');
        return false;
      }
    }
    return true;
  }

  return true;
}

function collectCaseData() {
  const getTextValue = (id) => {
    const field = document.getElementById(id);
    if (!field || field.value === undefined || field.value === null) return null;
    const text = String(field.value).trim();
    return text !== '' ? text : null;
  };

  const getNumberValue = (id) => {
    const text = getTextValue(id);
    if (text === null) return null;
    const number = Number(text);
    return Number.isFinite(number) ? number : null;
  };

  const mainIssue = getTextValue('main-issue') || 'other';
  const mainIssueOther = mainIssue === 'other' ? getTextValue('main-issue-other') : null;
  const workplace = getTextValue('workplace') || 'unknown';
  const workplaceOther = workplace === 'other' ? getTextValue('workplace-other') : null;
  const workPattern = getTextValue('work-pattern') || 'unknown';
  const paidLeave = getTextValue('paid-leave');
  const documents = getTextValue('documents') || 'unknown';
  const employmentDocType = ['both', 'no_contract', 'no_payslip'].includes(documents)
    ? (getTextValue('employment-doc-type') || 'unknown')
    : 'unknown';
  const payBasis = getTextValue('pay-basis') || 'unknown';
  const payAmount = getNumberValue('pay-amount');
  const pieceworkDescription = getTextValue('piecework-description');
  const payslipStatus = getTextValue('payslip-status') || 'unknown';
  const paymentMethod = getTextValue('payment-method') || 'unknown';
  const hoursUnknown = document.getElementById('hours-unknown')?.checked || false;
  const hoursPerWeek = hoursUnknown ? null : getNumberValue('hours-per-week');
  const hoursPerShift = getNumberValue('hours-per-shift');
  const overtime = getTextValue('overtime') || 'unknown';
  const breaks = getTextValue('breaks') || 'unknown';
  const visaThreat = getTextValue('visa-threat') || 'unknown';
  const immediateDanger = getTextValue('immediate-danger') || 'unknown';
  const safetyConcern = getTextValue('safety-concern') || 'unknown';
  const coercion = getTextValue('coercion') || 'unknown';

  return {
    mainIssue,
    mainIssueOther,
    description: getTextValue('description'),
    language: currentLanguage,
    workplace,
    workplaceOther,
    workTime: getSelectedWorkTimes(),
    workPattern,
    paidLeave: paidLeave === 'yes' ? true : paidLeave === 'no' ? false : null,
    documentAvailability: documents,
    employmentTypeOnDocuments: employmentDocType,
    pay: {
      payBasis,
      amount: ['hourly', 'per_shift', 'daily', 'weekly', 'monthly'].includes(payBasis) ? payAmount : null,
      description: payBasis === 'piecework' ? pieceworkDescription : null,
    },
    payslipStatus,
    paymentMethod,
    hoursPerWeek,
    hoursPerWeekKnown: !hoursUnknown && hoursPerWeek !== null,
    hoursPerShift,
    overtime,
    breaks,
    visaThreat,
    immediateDanger,
    safetyConcern,
    coercion
  };
}

function setLoadingState(isLoading) {
  const loadingState = document.getElementById('loading-state');
  const resultContent = document.getElementById('result-content');
  if (loadingState) loadingState.hidden = !isLoading;
  if (resultContent) resultContent.hidden = isLoading;
}

function renderResult(result) {
  const riskBadge = document.getElementById('result-risk');
  const summary = document.getElementById('result-summary');
  const issues = document.getElementById('result-issues');
  const evidence = document.getElementById('result-evidence');
  const nextSteps = document.getElementById('result-next-steps');
  const questions = document.getElementById('result-questions');
  const sources = document.getElementById('result-sources');
  const title = document.getElementById('result-title');

  if (title) {
    title.textContent = currentLanguage === 'en' ? 'Check result' : 'Kết quả kiểm tra';
  }
  if (riskBadge) {
    const riskLevel = String(result?.risk_level || 'medium').toUpperCase();
    riskBadge.textContent = riskLevel;
  }
  if (summary) {
    summary.textContent = result?.summary || 'No summary available.';
  }

  const renderList = (node, items) => {
    if (!node) return;
    node.innerHTML = '';
    const values = Array.isArray(items) ? items : [];
    values.filter((item) => item !== null && item !== undefined && String(item).trim() !== '').forEach((item) => {
      const li = document.createElement('li');
      li.textContent = String(item);
      node.appendChild(li);
    });
  };

  renderList(issues, result?.issues || []);
  renderList(evidence, result?.evidence || []);
  renderList(nextSteps, result?.next_steps || []);
  renderList(questions, result?.clarification_questions || []);

  if (sources) {
    sources.innerHTML = '';
    const sourceList = Array.isArray(result?.sources) ? result.sources : [];
    if (!sourceList.length) {
      sources.textContent = 'No official sources identified for this situation.';
      return;
    }

    sourceList.forEach((item) => {
      const card = document.createElement('div');
      card.className = 'source-item';
      const titleText = item?.title || 'Official source';
      const org = item?.organisation || '';
      const url = item?.url || '#';
      card.innerHTML = `<strong>${titleText}</strong><br><span>${org}</span><br><a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
      sources.appendChild(card);
    });
  }
}

async function sendCaseToBackend() {
  const payload = collectCaseData();
  const response = await fetch('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}));
    throw new Error(errorPayload.error || 'Unable to analyze case.');
  }

  return response.json();
}

function bindNavigation() {
  const backBtn = document.getElementById('back-btn');
  const continueBtn = document.getElementById('continue-btn');

  backBtn?.addEventListener('click', () => {
    if (currentStep > 1) {
      showStep(currentStep - 1);
    }
  });

  continueBtn?.addEventListener('click', async () => {
    if (!validateStep(currentStep)) return;

    if (currentStep < 4) {
      showStep(currentStep + 1);
      return;
    }

    continueBtn.disabled = true;
    continueBtn.textContent = currentLanguage === 'en' ? 'Analyzing...' : 'Đang phân tích...';
    setLoadingState(true);

    try {
      const result = await sendCaseToBackend();
      renderResult(result);
      showStep(5);
    } catch (error) {
      console.error(error);
      const summary = document.getElementById('result-summary');
      if (summary) {
        summary.textContent = currentLanguage === 'en'
          ? 'We could not generate guidance right now. Please try again in a moment.'
          : 'Không thể tạo hướng dẫn ngay lúc này. Vui lòng thử lại sau.';
      }
      setLoadingState(false);
    } finally {
      continueBtn.disabled = false;
      continueBtn.textContent = currentLanguage === 'en' ? 'Continue →' : 'Tiếp tục →';
    }
  });
}

function bindLanguageToggle() {
  const toggle = document.getElementById('language-toggle');
  toggle?.addEventListener('click', () => {
    setLanguage(currentLanguage === 'vi' ? 'en' : 'vi');
  });
}

function initialize() {
  bindChoiceButtons();
  bindLanguageToggle();
  bindNavigation();

  ['main-issue', 'workplace', 'documents', 'pay-basis'].forEach((id) => {
    const field = document.getElementById(id);
    field?.addEventListener('change', updateConditionalFields);
  });

  updateConditionalFields();
  applyTranslations();
  showStep(1);
}

initialize();
