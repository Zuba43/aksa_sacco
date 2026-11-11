from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime
from app.models import User, Loan, Savings, Expense, FineFee
from app import db

finance_bp = Blueprint('finance', __name__, url_prefix='/finance')

@finance_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ['finance', 'treasurer', 'chair']:
        flash('Access restricted to Finance & Treasury Officers.', 'danger')
        return redirect(url_for('auth.login'))

    # 0. Automatically evaluate loan status updates (Tenure defaults & Full settlements)
    all_loans = Loan.query.order_by(Loan.date_applied.desc()).all()
    for loan in all_loans:
        loan.check_and_update_status()
    db.session.commit()

    # 1. Core Capital Pools
    total_savings = db.session.query(func.sum(Savings.amount)).scalar() or 0.0
    total_fines = db.session.query(func.sum(FineFee.amount)).scalar() or 0.0
    
    # 2. Loan Calculations & Profits
    total_disbursed = 0.0
    unpaid_loan_balance = 0.0
    loan_profits = 0.0  # Total interest expected or earned on loans
    total_repayments_collected = 0.0

    for loan in all_loans:
        total_due = loan.total_due                # Accessed as a property
        loan.total_repaid_calc = loan.amount_repaid
        loan.balance_calc = loan.balance_remaining # Accessed as a property

        total_repayments_collected += loan.amount_repaid

        if loan.status in ['Approved', 'Active', 'Fully Paid', 'Defaulted']:
            total_disbursed += loan.amount_requested
            loan_profits += (loan.amount_requested * (loan.interest_rate / 100))

        if loan.status in ['Approved', 'Active', 'Defaulted']:
            unpaid_loan_balance += loan.balance_calc

    # 3. Growth Metrics Calculations
    # Actual Growth = Total Savings + Total Collected Repayments + Fines
    actual_growth = total_savings + total_repayments_collected + total_fines

    # Projected Growth = Actual Growth + Outstanding Expected Loan Balances + Projected Interest
    projected_growth = actual_growth + unpaid_loan_balance + loan_profits

    # 4. Risk & Status Breakdown Counts
    performing_count = Loan.query.filter(Loan.status.in_(['Approved', 'Active'])).count()
    fully_paid_count = Loan.query.filter_by(status='Fully Paid').count()
    pending_count = Loan.query.filter_by(status='Pending').count()
    default_count = Loan.query.filter_by(status='Defaulted').count()

    npl_amount = db.session.query(func.sum(Loan.amount_requested)).filter(
        Loan.status == 'Defaulted'
    ).scalar() or 0.0

    npl_ratio = (npl_amount / total_disbursed * 100) if total_disbursed > 0 else 0.0

    # 5. Purpose Breakdown
    tuition_total = db.session.query(func.sum(Loan.amount_requested)).filter(Loan.loan_type == 'emergency').scalar() or 0.0
    startup_total = db.session.query(func.sum(Loan.amount_requested)).filter(Loan.loan_type == 'Business startup').scalar() or 0.0
    others_total = db.session.query(func.sum(Loan.amount_requested)).filter(Loan.loan_type == 'general').scalar() or 0.0

    tuition_count = Loan.query.filter_by(loan_type='emergency').count()
    startup_count = Loan.query.filter_by(loan_type='Business startup').count()
    others_count = Loan.query.filter_by(loan_type='general').count()

    # 6. Personal Member Data for Logged-In Officer (Wallet Modal)
    personal_savings = Savings.query.filter_by(user_id=current_user.id).order_by(Savings.date_recorded.desc()).all()
    current_user_savings = sum(s.amount for s in personal_savings)

    # 7. Global Transactions for All Members
    all_savings_transactions = db.session.query(Savings, User).join(User, Savings.user_id == User.id).order_by(Savings.date_recorded.desc()).all()
    
    all_members = User.query.order_by(User.fname.asc()).all()
    all_fines_transactions = db.session.query(FineFee, User)\
        .join(User, FineFee.user_id == User.id)\
        .order_by(FineFee.date_recorded.desc()).all()
    
    all_expenses_transactions = db.session.query(Expense, User)\
        .join(User, Expense.recorded_by == User.id)\
        .order_by(Expense.date_recorded.desc()).all()

    return render_template(
        'finance/dashboard.html',
        actual_growth=actual_growth,
        projected_growth=projected_growth,
        loan_profits=loan_profits,
        unpaid_loan_balance=unpaid_loan_balance,
        total_savings=total_savings,
        all_fines_transactions=all_fines_transactions,
        all_expenses_transactions=all_expenses_transactions,
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
        all_savings_transactions=all_savings_transactions,
        all_repayments_transactions=[],  # Omitted since LoanRepayment model is bypassed
        all_members=all_members,
    )


# ================= ADMIN / TREASURER ACTION ROUTES =================

@finance_bp.route('/admin/record-loan', methods=['POST'])
@login_required
def admin_record_loan():
    if current_user.role not in ['finance', 'treasurer', 'chair']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('finance.dashboard'))

    try:
        user_id = request.form.get('user_id')
        loan_type = request.form.get('loan_type', 'General')
        amount_requested = float(request.form.get('amount_requested', 0))
        status = request.form.get('status', 'Active')

        date_applied_str = request.form.get('date_applied')
        if date_applied_str:
            loan_date = datetime.strptime(date_applied_str, '%Y-%m-%dT%H:%M')
        else:
            loan_date = datetime.utcnow()

        new_loan = Loan(
            user_id=user_id,
            loan_type=loan_type,
            amount_requested=amount_requested,
            interest_rate=10.0,
            tenure_months=3,
            status=status,
            guarantor_name="Pre-Deployment Record",
            guarantor_email="N/A",
            guarantor_phone="N/A",
            date_applied=loan_date
        )
        db.session.add(new_loan)
        db.session.commit()
        flash('Historical loan successfully recorded with custom issuance date.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error recording loan: {str(e)}', 'danger')

    return redirect(url_for('finance.dashboard'))


@finance_bp.route('/admin/make-expense', methods=['POST'])
@login_required
def admin_make_expense():
    if current_user.role not in ['finance', 'treasurer', 'chair']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('finance.dashboard'))

    try:
        title = request.form.get('title')
        amount = float(request.form.get('amount', 0))
        category = request.form.get('category', 'Administrative')
        
        date_str = request.form.get('date_recorded')
        if date_str:
            date_recorded = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            date_recorded = datetime.utcnow()

        new_expense = Expense(
            title=title,
            amount=amount,
            category=category,
            recorded_by=current_user.id,
            date_recorded=date_recorded
        )
        db.session.add(new_expense)
        db.session.commit()
        flash('Operational expense logged successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error logging expense: {str(e)}', 'danger')

    return redirect(url_for('finance.dashboard'))


@finance_bp.route('/admin/record-fine', methods=['POST'])
@login_required
def admin_record_fine():
    if current_user.role not in ['finance', 'treasurer', 'chair']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('finance.dashboard'))

    try:
        user_id = request.form.get('user_id')
        fee_type = request.form.get('fee_type', 'Penalty')
        amount = float(request.form.get('amount', 0))
        
        date_str = request.form.get('date_recorded')
        if date_str:
            date_recorded = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            date_recorded = datetime.utcnow()

        new_fine = FineFee(
            user_id=user_id,
            fee_type=fee_type,
            amount=amount,
            status='Unpaid',
            date_recorded=date_recorded
        )
        db.session.add(new_fine)
        db.session.commit()
        flash('Fine or fee recorded successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error recording fine: {str(e)}', 'danger')

    return redirect(url_for('finance.dashboard'))

@finance_bp.route('/admin/pay-fine/<int:fine_id>', methods=['POST'])
@login_required
def admin_pay_fine(fine_id):
    if current_user.role not in ['finance', 'treasurer', 'chair']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('finance.dashboard'))

    fine = FineFee.query.get_or_404(fine_id)
    try:
        fine.status = 'Paid'
        db.session.commit()
        flash(f'Fine #{fine.id} marked as Paid successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating fine: {str(e)}', 'danger')

    return redirect(url_for('finance.dashboard'))