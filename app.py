import os
import json
import joblib
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get("SECRET_KEY", "ai-loan-eligibility-secret-key-2026")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'models')
DATA_DIR = os.path.join(BASE_DIR, 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

APPROVAL_MODEL_PATH = os.path.join(MODEL_DIR, 'loan_approval_model.pkl')
AMOUNT_MODEL_PATH = os.path.join(MODEL_DIR, 'loan_amount_model.pkl')

# Load saved scikit-learn ML models
try:
    approval_model = joblib.load(APPROVAL_MODEL_PATH)
    amount_model = joblib.load(AMOUNT_MODEL_PATH)
    print("ML models loaded successfully.")
except Exception as e:
    print(f"Error loading models: {e}")
    approval_model = None
    amount_model = None


# Helper functions for users.json storage
def load_users():
    """
    Safely loads user records from data/users.json.
    Creates directory and initial admin user if missing.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {
                "password_hash": generate_password_hash("admin123")
            }
        }
        save_users(default_users)
        return default_users

    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading users.json: {e}")
        return {}


def save_users(users_dict):
    """
    Saves user records dictionary to data/users.json.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_dict, f, indent=2)


def calculate_emi(principal, tenure_months, annual_interest_rate=10.5):
    """
    Calculates Equated Monthly Installment (EMI) using standard formula:
    EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
    """
    if principal <= 0 or tenure_months <= 0:
        return 0.0

    r = (annual_interest_rate / 100.0) / 12.0
    n = float(tenure_months)

    if r == 0:
        return round(principal / n, 2)

    emi = principal * r * ((1.0 + r) ** n) / (((1.0 + r) ** n) - 1.0)
    return round(float(emi), 2)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration route.
    Stores username and hashed password in data/users.json.
    """
    if 'user' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not username:
            return render_template('register.html', error="Username is required.", username=username)

        if not password:
            return render_template('register.html', error="Password is required.", username=username)

        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match.", username=username)

        users = load_users()

        # Check for duplicate username (case-insensitive)
        for existing_user in users:
            if existing_user.lower() == username.lower():
                return render_template('register.html', error="Username already exists. Please choose a different username.", username=username)

        # Hash password using Werkzeug security
        users[username] = {
            "password_hash": generate_password_hash(password)
        }
        save_users(users)

        return render_template('login.html', success="Account created successfully! Please sign in with your credentials.")

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Multi-user authentication route.
    Validates user credentials against data/users.json using check_password_hash.
    """
    if 'user' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        users = load_users()

        user_data = None
        target_username = None
        for u_name, u_info in users.items():
            if u_name.lower() == username.lower():
                user_data = u_info
                target_username = u_name
                break

        if user_data and check_password_hash(user_data.get('password_hash', ''), password):
            session['user'] = target_username
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid username or password.", username=username)

    return render_template('login.html')


@app.route('/logout', methods=['GET'])
def logout():
    """
    Logs out user by clearing session.
    """
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/', methods=['GET'])
def home():
    """
    Protected Loan Eligibility Form Dashboard.
    """
    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    """
    Prediction endpoint accepting 10 customer input features in JSON format.
    Returns approval_probability, eligible_loan_amount, and estimated_emi.
    """
    if 'user' not in session:
        return jsonify({"error": "Unauthorized access. Please log in first."}), 401

    if not approval_model or not amount_model:
        return jsonify({"error": "ML models are not loaded properly."}), 500

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload."}), 400

    required_features = [
        "monthly_income",
        "employment_type",
        "credit_score",
        "existing_loans_count",
        "existing_emi_monthly",
        "dependents",
        "savings_balance",
        "loan_type",
        "requested_amount",
        "tenure_months"
    ]

    missing = [f for f in required_features if f not in data]
    if missing:
        return jsonify({"error": f"Missing required feature fields: {', '.join(missing)}"}), 400

    try:
        input_data = {
            "monthly_income": float(data["monthly_income"]),
            "employment_type": str(data["employment_type"]),
            "credit_score": float(data["credit_score"]),
            "existing_loans_count": float(data["existing_loans_count"]),
            "existing_emi_monthly": float(data["existing_emi_monthly"]),
            "dependents": float(data["dependents"]),
            "savings_balance": float(data["savings_balance"]),
            "loan_type": str(data["loan_type"]),
            "requested_amount": float(data["requested_amount"]),
            "tenure_months": float(data["tenure_months"])
        }

        df = pd.DataFrame([input_data])

        # 1. Loan Approval Probability
        approval_proba_arr = approval_model.predict_proba(df)[0]
        classes = list(getattr(approval_model, 'classes_', []))

        if 'Approved' in classes:
            approved_idx = classes.index('Approved')
            approval_prob = float(approval_proba_arr[approved_idx])
        else:
            approval_prob = float(approval_proba_arr[0])

        approval_probability = round(approval_prob, 4)

        # 2. Eligible Loan Amount
        amount_pred = amount_model.predict(df)[0]
        eligible_loan_amount = max(0.0, round(float(amount_pred), 2))

        # 3. Estimated Monthly EMI
        tenure_months = float(input_data["tenure_months"])
        estimated_emi = calculate_emi(eligible_loan_amount, tenure_months)

        return jsonify({
            "approval_probability": approval_probability,
            "eligible_loan_amount": eligible_loan_amount,
            "estimated_emi": estimated_emi
        }), 200

    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
