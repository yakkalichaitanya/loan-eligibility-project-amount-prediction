document.addEventListener('DOMContentLoaded', () => {
    const loanForm = document.getElementById('loanForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnSpinner = submitBtn.querySelector('.btn-spinner');
    
    const errorBanner = document.getElementById('errorBanner');
    const errorMessage = document.getElementById('errorMessage');
    
    const resultsSection = document.getElementById('resultsSection');
    const probabilityRing = document.getElementById('probabilityRing');
    const probabilityText = document.getElementById('probabilityText');
    const probabilityLabel = document.getElementById('probabilityLabel');
    const eligibleAmountText = document.getElementById('eligibleAmountText');
    const estimatedEmiText = document.getElementById('estimatedEmiText');

    // Indian Rupee Formatter
    const formatINR = (val) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0
        }).format(val);
    };

    // Clear error message displays
    const clearErrors = () => {
        document.querySelectorAll('.error-text').forEach(el => el.textContent = '');
        document.querySelectorAll('.input-error').forEach(el => el.classList.remove('input-error'));
        errorBanner.classList.add('hidden');
    };

    // Form Field Validation
    const validateForm = (data) => {
        let isValid = true;

        const setFieldError = (fieldId, msg) => {
            const errEl = document.getElementById(`err-${fieldId}`);
            const inputEl = document.getElementById(fieldId);
            if (errEl) errEl.textContent = msg;
            if (inputEl) inputEl.classList.add('input-error');
            isValid = false;
        };

        if (isNaN(data.monthly_income) || data.monthly_income <= 0) {
            setFieldError('monthly_income', 'Please enter a valid monthly income.');
        }

        if (!data.employment_type) {
            setFieldError('employment_type', 'Please select an employment type.');
        }

        if (isNaN(data.credit_score) || data.credit_score < 300 || data.credit_score > 900) {
            setFieldError('credit_score', 'Credit score must be between 300 and 900.');
        }

        if (isNaN(data.existing_loans_count) || data.existing_loans_count < 0) {
            setFieldError('existing_loans_count', 'Existing loans count cannot be negative.');
        }

        if (isNaN(data.existing_emi_monthly) || data.existing_emi_monthly < 0) {
            setFieldError('existing_emi_monthly', 'Existing EMI cannot be negative.');
        }

        if (isNaN(data.dependents) || data.dependents < 0) {
            setFieldError('dependents', 'Dependents count cannot be negative.');
        }

        if (isNaN(data.savings_balance) || data.savings_balance < 0) {
            setFieldError('savings_balance', 'Savings balance cannot be negative.');
        }

        if (!data.loan_type) {
            setFieldError('loan_type', 'Please select a loan type.');
        }

        if (isNaN(data.requested_amount) || data.requested_amount <= 0) {
            setFieldError('requested_amount', 'Please enter a valid requested loan amount.');
        }

        if (isNaN(data.tenure_months) || data.tenure_months < 6 || data.tenure_months > 360) {
            setFieldError('tenure_months', 'Tenure must be between 6 and 360 months.');
        }

        return isValid;
    };

    // Set UI Loading state
    const setLoading = (loading) => {
        if (loading) {
            submitBtn.disabled = true;
            btnText.textContent = 'Evaluating Eligibility...';
            btnSpinner.classList.remove('hidden');
            errorBanner.classList.add('hidden');
        } else {
            submitBtn.disabled = false;
            btnText.textContent = 'Check Loan Eligibility';
            btnSpinner.classList.add('hidden');
        }
    };

    // Animate Radial Progress Ring for Approval Probability
    const updateProbabilityRing = (probabilityDecimal) => {
        const radius = 50;
        const circumference = 2 * Math.PI * radius; // 314.159
        const percent = Math.min(Math.max(probabilityDecimal, 0), 1);
        const offset = circumference - (percent * circumference);

        probabilityRing.style.strokeDashoffset = offset;
        const percentDisplay = Math.round(percent * 100);
        probabilityText.textContent = `${percentDisplay}%`;

        // Color coding ring based on score
        if (percent >= 0.75) {
            probabilityRing.setAttribute('stroke', '#10b981'); // Emerald green
            probabilityLabel.textContent = 'High Approval Chance';
            probabilityLabel.style.color = '#34d399';
        } else if (percent >= 0.45) {
            probabilityRing.setAttribute('stroke', '#f59e0b'); // Amber
            probabilityLabel.textContent = 'Moderate Approval Chance';
            probabilityLabel.style.color = '#fbbf24';
        } else {
            probabilityRing.setAttribute('stroke', '#f43f5e'); // Rose red
            probabilityLabel.textContent = 'Low Approval Chance';
            probabilityLabel.style.color = '#f87171';
        }
    };

    // Form Submission Handler
    loanForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearErrors();

        // Collect form data matching exact backend feature names
        const payload = {
            monthly_income: parseFloat(document.getElementById('monthly_income').value),
            employment_type: document.getElementById('employment_type').value,
            credit_score: parseFloat(document.getElementById('credit_score').value),
            existing_loans_count: parseFloat(document.getElementById('existing_loans_count').value),
            existing_emi_monthly: parseFloat(document.getElementById('existing_emi_monthly').value),
            dependents: parseFloat(document.getElementById('dependents').value),
            savings_balance: parseFloat(document.getElementById('savings_balance').value),
            loan_type: document.getElementById('loan_type').value,
            requested_amount: parseFloat(document.getElementById('requested_amount').value),
            tenure_months: parseFloat(document.getElementById('tenure_months').value)
        };

        if (!validateForm(payload)) {
            return;
        }

        setLoading(true);

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `Server error: ${response.status}`);
            }

            // Display Results
            updateProbabilityRing(result.approval_probability);
            eligibleAmountText.textContent = formatINR(result.eligible_loan_amount);
            estimatedEmiText.textContent = `${formatINR(result.estimated_emi)}/mo`;

            resultsSection.classList.remove('hidden');
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        } catch (err) {
            errorMessage.textContent = err.message || 'Failed to communicate with prediction server. Please try again.';
            errorBanner.classList.remove('hidden');
        } finally {
            setLoading(false);
        }
    });
});
