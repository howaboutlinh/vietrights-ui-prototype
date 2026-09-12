let currentLanguage = 'vi';
let currentStep = 1;
let isAnalyzing = false;
let analysisAbortController = null;
let translations = null;

const requiredStepFieldIds = {
  1: ['main-issues'],
  2: ['workplace', 'work-pattern', 'paid-leave', 'documents', 'pay-basis', 'payslip-status', 'payment-method'],
  3: ['hours-per-week', 'overtime', 'breaks'],
  4: ['visa-threat', 'immediate-danger', 'safety-concern', 'coercion']
};

/**
 * Retrieve translation string by dot-separated key for current language.
 */
function t(keyPath, defaultText = '') {
  if (!translations || !translations[currentLanguage]) {
    return defaultText;
  }
  const parts = keyPath.split('.');
  let current = translations[currentLanguage];
  for (const part of parts) {
    if (current && typeof current === 'object' && part in current) {
      current = current[part];
    } else {
      return defaultText;
    }
  }
  return typeof current === 'string' ? current : defaultText;
}

/**
 * Load localization dictionary from external UTF-8 JSON file.
 */
async function loadTranslations() {
  try {
    const response = await fetch('/static/locales/translations.json');
    if (response.ok) {
      translations = await response.json();
    } else {
      console.error('Failed to load translations file:', response.statusText);
    }
  } catch (error) {
    console.error('Error fetching localization resource:', error);
  }
}

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

function getSelectedIssues() {
  return [...document.querySelectorAll('input[name="main-issues"]:checked')]
    .map((checkbox) => checkbox.value)
    .filter(Boolean);
}

function updateConditionalFields() {
  const selectedIssues = getSelectedIssues();
  const mainIssueOtherWrap = document.getElementById('main-issue-other-wrap');
  if (mainIssueOtherWrap) {
    const shouldShow = selectedIssues.includes('other');
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
    const labelKey = `pay_labels.${value}`;
    const dynamicLabel = t(labelKey, '');

    if (value && dynamicLabel) {
      payAmountLabel.textContent = dynamicLabel;
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
  document.documentElement.lang = currentLanguage;
  applyTranslations();
  updateProgressUI();
  updateSidebarUI();
  updateConditionalFields();
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach((node) => {
    const key = node.getAttribute('data-i18n');
    const value = t(key, '');
    if (value) {
      node.textContent = value;
    }
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach((node) => {
    const key = node.getAttribute('data-i18n-placeholder');
    const value = t(key, '');
    if (value) {
      node.placeholder = value;
    }
  });

  document.querySelectorAll('[data-i18n-aria-label]').forEach((node) => {
    const key = node.getAttribute('data-i18n-aria-label');
    const value = t(key, '');
    if (value) node.setAttribute('aria-label', value);
  });

  const languageToggle = document.getElementById('language-toggle');
  if (languageToggle) {
    languageToggle.textContent = t('lang_toggle', currentLanguage === 'vi' ? 'VI / EN' : 'EN / VI');
    languageToggle.setAttribute('aria-label', t('lang_toggle_label', currentLanguage === 'vi' ? 'Switch to English' : 'Chuyển sang tiếng Việt'));
    languageToggle.setAttribute('aria-pressed', String(currentLanguage === 'en'));
  }

  const stepLabel = document.getElementById('step-label');
  if (stepLabel) {
    stepLabel.textContent = t(`step_labels.${currentStep}`, '');
  }

  const continueBtn = document.getElementById('continue-btn');
  if (continueBtn) {
    continueBtn.textContent = currentStep === 4
      ? t('btn_analyze', 'Analyze case →')
      : t('btn_continue', 'Continue →');
  }

  const backBtn = document.getElementById('back-btn');
  if (backBtn && !backBtn.hidden) {
    backBtn.textContent = t('btn_back', '← Back');
  }

  const retryBtn = document.getElementById('retry-btn');
  if (retryBtn) {
    retryBtn.textContent = t('btn_retry', 'Try again');
  }

  const resultTitle = document.getElementById('result-title');
  if (resultTitle) {
    resultTitle.textContent = t('result.title', 'Check result');
  }
}

function updateSidebarUI() {
  document.querySelectorAll('.step-item').forEach((item) => {
    const itemStep = Number(item.dataset.sideStep);
    const subtextNode = item.querySelector('small');

    const isComplete = itemStep < currentStep;
    const isActive = itemStep === currentStep;

    item.classList.toggle('is-complete', isComplete);
    item.classList.toggle('is-active', isActive);

    if (subtextNode) {
      if (isComplete) {
        subtextNode.textContent = t('sidebar_status_complete', 'Completed');
      } else if (isActive) {
        if (itemStep === 5) {
          subtextNode.textContent = t('sidebar_status_viewing', 'Viewing guidance');
        } else {
          subtextNode.textContent = t('sidebar_status_active', 'In progress');
        }
      } else {
        subtextNode.textContent = t(`sidebar_pending_step_${itemStep}`, '');
      }
    }
  });
}

function updateProgressUI() {
  const progressFill = document.getElementById('progress-fill');
  const stepLabel = document.getElementById('step-label');
  const stepCount = document.getElementById('step-count');
  const backBtn = document.getElementById('back-btn');
  const continueBtn = document.getElementById('continue-btn');

  const progressMap = { 1: 20, 2: 40, 3: 60, 4: 80, 5: 100 };
  if (progressFill) progressFill.style.width = `${progressMap[currentStep] || 20}%`;
  if (stepLabel) stepLabel.textContent = t(`step_labels.${currentStep}`, '');
  if (stepCount) {
    const prefix = t('step_prefix', 'Step');
    stepCount.textContent = `${prefix} ${currentStep} / 5`;
  }
  if (backBtn) backBtn.hidden = currentStep === 1;
  if (continueBtn) {
    continueBtn.hidden = currentStep === 5;
    continueBtn.textContent = currentStep === 4
      ? t('btn_analyze', 'Analyze case →')
      : t('btn_continue', 'Continue →');
  }

  updateSidebarUI();
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
    const selectedIssues = getSelectedIssues();
    if (!selectedIssues.length) {
      showFieldError('main-issues', t('validation.main_issues', 'Please select at least one issue you are experiencing.'));
      return false;
    }
    if (selectedIssues.includes('other')) {
      const otherValue = valueOf('main-issue-other');
      if (!otherValue) {
        showFieldError('main-issue-other', t('validation.main_issue_other', 'Please describe your issue when selecting Other.'));
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

    if (!workplace) {
      showFieldError('workplace', t('validation.workplace', 'Please select your workplace industry.'));
      return false;
    }
    if (workplace === 'other' && !workplaceOther) {
      showFieldError('workplace', t('validation.workplace_other', 'Please specify your workplace.'));
      return false;
    }
    if (!workPattern) {
      showFieldError('work-pattern', t('validation.work_pattern', 'Please select your work pattern.'));
      return false;
    }
    if (!paidLeave) {
      showFieldError('paid-leave', t('validation.paid_leave', 'Please indicate paid leave status.'));
      return false;
    }
    if (!documents) {
      showFieldError('documents', t('validation.documents', 'Please indicate contract/payslip availability.'));
      return false;
    }
    const shouldRequireEmploymentDoc = ['both', 'no_contract', 'no_payslip'].includes(documents);
    if (shouldRequireEmploymentDoc && !employmentDoc) {
      showFieldError('employment-doc-type', t('validation.employment_doc_type', 'Please select employment type on documents.'));
      return false;
    }
    if (!payBasis) {
      showFieldError('pay-basis', t('validation.pay_basis', 'Please select how you are paid.'));
      return false;
    }
    if (['hourly', 'per_shift', 'daily', 'weekly', 'fortnightly', 'monthly'].includes(payBasis) && !payAmount) {
      showFieldError('pay-amount', t('validation.pay_amount', 'Please enter your pay amount.'));
      return false;
    }
    if (payBasis === 'piecework' && !pieceworkDescription) {
      showFieldError('piecework-description', t('validation.piecework_description', 'Please describe how your pay is calculated.'));
      return false;
    }
    if (!payslipStatus) {
      showFieldError('payslip-status', t('validation.payslip_status', 'Please indicate if you receive payslips.'));
      return false;
    }
    if (!paymentMethod) {
      showFieldError('payment-method', t('validation.payment_method', 'Please select your payment method.'));
      return false;
    }
    return true;
  }

  if (step === 3) {
    const hasWorkTimes = getSelectedWorkTimes().length > 0;
    const hoursUnknown = document.getElementById('hours-unknown')?.checked;
    const hoursPerWeek = valueOf('hours-per-week');
    const overtime = valueOf('overtime');
    const breaks = valueOf('breaks');

    if (!hasWorkTimes) {
      showFieldError('work-time', t('validation.work_time', 'Please select at least one work schedule option.'));
      return false;
    }
    if (!hoursUnknown && !hoursPerWeek) {
      showFieldError('hours-per-week', t('validation.hours_per_week', 'Please enter weekly hours or check "Not sure".'));
      return false;
    }
    if (!overtime) {
      showFieldError('overtime', t('validation.overtime', 'Please indicate if you work overtime.'));
      return false;
    }
    if (!breaks) {
      showFieldError('breaks', t('validation.breaks', 'Please indicate if you get rest breaks.'));
      return false;
    }
    return true;
  }

  if (step === 4) {
    for (const id of ['visa-threat', 'immediate-danger', 'safety-concern', 'coercion']) {
      if (!valueOf(id)) {
        showFieldError(id, t('validation.risk_questions', 'Please select an answer for this question.'));
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

  const mainIssues = getSelectedIssues();
  const mainIssueOther = mainIssues.includes('other') ? getTextValue('main-issue-other') : null;
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
    mainIssues,
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
      amount: ['hourly', 'per_shift', 'daily', 'weekly', 'fortnightly', 'monthly'].includes(payBasis) ? payAmount : null,
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
  if (resultContent && isLoading) resultContent.hidden = true;
}

function isSafeUrl(urlStr) {
  if (!urlStr || typeof urlStr !== 'string') return false;
  const trimmed = urlStr.trim();
  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
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
    title.textContent = t('result.title', 'Check result');
  }
  if (riskBadge) {
    const riskLevel = String(result?.risk_level || 'medium').toLowerCase();
    riskBadge.textContent = t(`result.risk_${riskLevel}`, riskLevel.toUpperCase());
  }
  if (summary) {
    summary.textContent = result?.summary || t('result.no_summary', 'No summary available.');
  }

  const renderList = (node, items) => {
    if (!node) return;
    node.textContent = '';
    const values = Array.isArray(items) ? items : [];
    values
      .filter((item) => item !== null && item !== undefined && String(item).trim() !== '')
      .forEach((item) => {
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
    sources.textContent = '';
    const sourceList = Array.isArray(result?.sources) ? result.sources : [];
    if (!sourceList.length) {
      const emptyNote = document.createElement('p');
      emptyNote.textContent = t('result.no_sources', 'No official sources identified for this situation.');
      sources.appendChild(emptyNote);
      return;
    }

    sourceList.forEach((item) => {
      const card = document.createElement('div');
      card.className = 'source-item';

      const titleEl = document.createElement('strong');
      titleEl.textContent = String(item?.title || t('result.default_source_title', 'Official source'));
      card.appendChild(titleEl);

      if (item?.organisation) {
        const orgEl = document.createElement('span');
        orgEl.className = 'source-org';
        orgEl.textContent = String(item.organisation);
        card.appendChild(orgEl);
      }

      const rawUrl = String(item?.url || '').trim();
      if (isSafeUrl(rawUrl)) {
        const linkEl = document.createElement('a');
        linkEl.className = 'source-link';
        linkEl.href = rawUrl;
        linkEl.textContent = rawUrl;
        linkEl.target = '_blank';
        linkEl.rel = 'noopener noreferrer';
        card.appendChild(linkEl);
      }

      sources.appendChild(card);
    });
  }
}

async function sendCaseToBackend(signal) {
  const payload = collectCaseData();
  const response = await fetch('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal
  });

  const contentType = response.headers.get('content-type') || '';
  let responseData;
  if (contentType.includes('application/json')) {
    responseData = await response.json();
  } else {
    const rawText = await response.text();
    throw new Error(rawText || t('error.invalid_response', 'Server returned non-JSON response.'));
  }

  if (!response.ok || responseData.status === 'error') {
    const errorMsg = responseData?.error || t('error.unable_to_analyze', 'Unable to analyze case.');
    throw new Error(errorMsg);
  }

  return responseData;
}

async function runAnalysis() {
  if (isAnalyzing) return;

  const backBtn = document.getElementById('back-btn');
  const continueBtn = document.getElementById('continue-btn');
  const resultContent = document.getElementById('result-content');
  const errorBox = document.getElementById('analysis-error');
  const errorMessage = document.getElementById('analysis-error-message');
  const errorTitle = document.getElementById('analysis-error-title');

  showStep(5);
  setLoadingState(true);
  if (errorBox) errorBox.hidden = true;
  if (resultContent) resultContent.hidden = true;

  isAnalyzing = true;
  if (continueBtn) continueBtn.disabled = true;
  if (backBtn) backBtn.disabled = true;

  analysisAbortController = new AbortController();
  const timeoutMs = 30000;
  const timeoutId = setTimeout(() => {
    analysisAbortController.abort();
  }, timeoutMs);

  try {
    const result = await sendCaseToBackend(analysisAbortController.signal);
    clearTimeout(timeoutId);

    renderResult(result);
    setLoadingState(false);
    if (resultContent) resultContent.hidden = false;
    if (errorBox) errorBox.hidden = true;
  } catch (error) {
    clearTimeout(timeoutId);
    console.error('Analyze request failed:', error);

    setLoadingState(false);
    if (resultContent) resultContent.hidden = true;

    if (errorBox && errorMessage) {
      let displayError = error.message || '';
      if (error.name === 'AbortError') {
        displayError = t('error.timeout', 'Request timed out (30 seconds). Please check your internet connection and try again.');
      } else if (!displayError) {
        displayError = t('error.unexpected', 'An unexpected error occurred while analyzing the case.');
      }

      if (errorTitle) {
        errorTitle.textContent = t('error.title', 'Analysis could not be completed');
      }
      errorMessage.textContent = displayError;
      errorBox.hidden = false;
    }
  } finally {
    isAnalyzing = false;
    if (continueBtn) continueBtn.disabled = false;
    if (backBtn) backBtn.disabled = false;
    updateProgressUI();
  }
}

function bindNavigation() {
  const backBtn = document.getElementById('back-btn');
  const continueBtn = document.getElementById('continue-btn');
  const retryBtn = document.getElementById('retry-btn');

  backBtn?.addEventListener('click', () => {
    if (isAnalyzing) return;
    if (currentStep > 1) {
      showStep(currentStep - 1);
    }
  });

  continueBtn?.addEventListener('click', async () => {
    if (isAnalyzing) return;
    if (!validateStep(currentStep)) return;

    if (currentStep < 4) {
      showStep(currentStep + 1);
      return;
    }

    await runAnalysis();
  });

  retryBtn?.addEventListener('click', async () => {
    if (isAnalyzing) return;
    await runAnalysis();
  });
}

function bindLanguageToggle() {
  const toggle = document.getElementById('language-toggle');
  toggle?.addEventListener('click', async () => {
    setLanguage(currentLanguage === 'vi' ? 'en' : 'vi');

    // Analysis copy is generated by the backend in the selected language.
    // Regenerate an already-visible result so the page never remains bilingual.
    const resultContent = document.getElementById('result-content');
    if (currentStep === 5 && resultContent && !resultContent.hidden && !isAnalyzing) {
      await runAnalysis();
    }
  });
}

function bindIssueCheckboxes() {
  document.querySelectorAll('input[name="main-issues"]').forEach((checkbox) => {
    checkbox.addEventListener('change', () => {
      updateConditionalFields();
      clearFieldErrors();
    });
  });
}

async function initialize() {
  bindChoiceButtons();
  bindIssueCheckboxes();
  bindLanguageToggle();
  bindNavigation();

  ['workplace', 'documents', 'pay-basis'].forEach((id) => {
    const field = document.getElementById(id);
    field?.addEventListener('change', updateConditionalFields);
  });

  await loadTranslations();
  updateConditionalFields();
  applyTranslations();
  showStep(1);
}

document.addEventListener('DOMContentLoaded', initialize);
