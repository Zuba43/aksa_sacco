from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import User, Loan, Savings, LoanRepayment
from app import db

finance_bp = Blueprint('finance', __name__, url_prefix='/finance')

@finance_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ['finance', 'treasurer', 'chair']:
        flash('Access restricted to Finance & Treasury Officers.', 'danger')
        return redirect(url_for('auth.login'))

    # 1. Total Financial Metrics
    total_savings = db.session.query(func.sum(Savings.amount)).scalar() or 0.0
    total_disbursed = db.session.query(func.sum(Loan.amount_requested)).filter(
        Loan.status.in_(['Approved', 'Active', 'Fully Paid', 'Defaulted'])
    ).scalar() or 0.0

    # 2. Risk & Status Breakdown Counts
    performing_count = Loan.query.filter(Loan.status.in_(['Approved', 'Active'])).count()
    fully_paid_count = Loan.query.filter_by(status='Fully Paid').count()
    pending_count = Loan.query.filter_by(status='Pending').count()
    default_count = Loan.query.filter(Loan.status.in_(['Defaulted', 'Rejected'])).count()

    npl_amount = db.session.query(func.sum(Loan.amount_requested)).filter(
        Loan.status.in_(['Defaulted'])
    ).scalar() or 0.0

    npl_ratio = (npl_amount / total_disbursed * 100) if total_disbursed > 0 else 0.0

    # 3. Purpose Breakdown
    tuition_total = db.session.query(func.sum(Loan.amount_requested)).filter(Loan.loan_type == 'emergency').scalar() or 0.0
    startup_total = db.session.query(func.sum(Loan.amount_requested)).filter(Loan.loan_type == 'Business startup').scalar() or 0.0
    others_total = db.session.query(func.sum(Loan.amount_requested)).filter(Loan.loan_type == 'general').scalar() or 0.0

    tuition_count = Loan.query.filter_by(loan_type='emergency').count()
    startup_count = Loan.query.filter_by(loan_type='Business startup').count()
    others_count = Loan.query.filter_by(loan_type='general').count()

    # 4. Fetch all loans and dynamically compute total repayments from LoanRepayment model
    all_loans = Loan.query.order_by(Loan.date_applied.desc()).all()

    for loan in all_loans:
        total_paid = sum(r.amount for r in loan.repayments) if loan.repayments else 0.0
        total_due = loan.amount_requested * (1 + (loan.interest_rate / 100))
        loan.total_repaid_calc = total_paid
        loan.balance_calc = max(0.0, total_due - total_paid)

    # 5. Personal Member Data for Logged-In Officer (Wallet Modal)
    personal_savings = Savings.query.filter_by(user_id=current_user.id).order_by(Savings.date_recorded.desc()).all()
    current_user_savings = sum(s.amount for s in personal_savings)

    # 6. Global Transactions for All Members (Explicitly joining User to guarantee member name display)
    all_savings_transactions = db.session.query(Savings, User).join(User, Savings.user_id == User.id).order_by(Savings.date_recorded.desc()).all()
    
    # Fetch all repayments with their associated loan and user info
    all_repayments_transactions = LoanRepayment.query.order_by(LoanRepayment.date_paid.desc()).all() if hasattr(LoanRepayment, 'date_paid') else LoanRepayment.query.all()

    return render_template(
        'finance/dashboard.html',
        total_savings=total_savings,
        total_disbursed=total_disbursed,
        performing_count=performing_count,
        fully_paid_count=fully_paid_count,
        pending_count=pending_count,
        default_count=default_count,
        npl_amount=npl_amount,
        npl_ratio=npl_ratio,
        tuition_total=tuition_total,
        startup_total=startup_total,
        others_total=others_total,
        tuition_count=tuition_count,
        startup_count=startup_count,
        others_count=others_count,
        all_loans=all_loans,
        savings=personal_savings,
        current_user_savings=current_user_savings,
        # Passed as tuples (savings_obj, user_obj) to completely eliminate 'Unknown Member' issues:
        all_savings_transactions=all_savings_transactions,
        all_repayments_transactions=all_repayments_transactions
    )