from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from datetime import datetime
from app.models import User, Loan, Savings, Expense, FineFee
from app import db


finance_bp = Blueprint('finance', __name__, url_prefix='/finance')

@finance_bp.app_template_filter("compact_num")
def compact_num(value):
    if value is None:
        val = 0.0
    elif isinstance(value, (int, float)):
        val = float(value)
    else:
        try:
            # Clean commas and whitespace from strings like '425,000.00'
            cleaned = str(value).replace(',', '').strip()
            val = float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            val = 0.0

    if val >= 1_000_000_000:
        return f"{val / 1_000_000_000:.3f}".rstrip("0").rstrip(".") + "B"
    elif val >= 1_000_000:
        return f"{val / 1_000_000:.3f}".rstrip("0").rstrip(".") + "M"
    elif val >= 1_000:
        return f"{val / 1_000:.2f}".rstrip("0").rstrip(".") + "K"
    return f"{val:,.0f}"


@finance_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role not in ["finance", "treasurer", "chair"]:
        flash("Access restricted to Finance & Treasury Officers.", "danger")
        return redirect(url_for("auth.login"))

    # 0. Automatically evaluate loan status updates (Tenure defaults & Full settlements)
    all_loans = Loan.query.order_by(Loan.date_applied.desc()).all()
    for loan in all_loans:
        loan.check_and_update_status()
    db.session.commit()

    # 1. Core Capital Pools & Fee Breakdowns
    total_savings = db.session.query(func.sum(Savings.amount)).scalar() or 0.0

    # Membership Fees (matches any fee_type containing 'membership', case-insensitive)
    membership_fees = (
        db.session.query(func.sum(FineFee.amount))
        .filter(func.lower(FineFee.fee_type).like("%membership%"))
        .scalar()
        or 0.0
    )

    top_savers = (
        db.session.query(
            User,
            func.coalesce(func.sum(Savings.amount), 0.0).label("total_savings")
        )
        .outerjoin(Savings, User.id == Savings.user_id)
        .group_by(User.id)
        .order_by(func.sum(Savings.amount).desc())
        .all()
    )

    total_fines_fees = (
        db.session.query(func.sum(FineFee.amount))
        .filter(~func.lower(FineFee.fee_type).like("%membership%"))
        .scalar() or 0.0
    )

    # 2. Loan Calculations & Profits
    unpaid_loans = 0.0
    loan_profits = 0.0  # Total interest expected or earned on loans

    for loan in all_loans:
        loan.total_repaid_calc = loan.amount_repaid
        loan.balance_calc = loan.balance_remaining

        if loan.status in ["Approved", "Active", "Fully Paid", "Defaulted"]:
            loan_profits += loan.amount_requested * (loan.interest_rate / 100.0)

        if loan.status in ["Approved", "Active", "Defaulted"]:
            unpaid_loans += loan.balance_calc

    # 3. Financial Year Cashflow Chart Data (Starting November 06)
    now = datetime.utcnow()
    if now.month > 11 or (now.month == 11 and now.day >= 6):
        fy_start_year = now.year
    else:
        fy_start_year = now.year - 1
        
    fy_start_date = datetime(fy_start_year, 11, 6)

    fy_labels = []
    fy_disbursements = []
    fy_repayments = []

    curr = datetime(fy_start_date.year, fy_start_date.month, 1)
    while curr <= datetime(now.year, now.month, 1):
        fy_labels.append(curr.strftime("%b %Y"))
        
        m_disbursements = db.session.query(func.coalesce(func.sum(Loan.amount_requested), 0.0)).filter(
            extract('year', Loan.date_applied) == curr.year,
            extract('month', Loan.date_applied) == curr.month,
            Loan.date_applied >= fy_start_date
        ).scalar()
        
        m_repayments = db.session.query(func.coalesce(func.sum(Loan.amount_repaid), 0.0)).filter(
            extract('year', Loan.date_applied) == curr.year,
            extract('month', Loan.date_applied) == curr.month,
            Loan.date_applied >= fy_start_date
        ).scalar()
        
        fy_disbursements.append(m_disbursements)
        fy_repayments.append(m_repayments)
        
        if curr.month == 12:
            curr = datetime(curr.year + 1, 1, 1)
        else:
            curr = datetime(curr.year, curr.month + 1, 1)

    # 4. Risk & Status Breakdown Counts
    performing_count = Loan.query.filter(
        Loan.status.in_(["Approved", "Active"])
    ).count()
    fully_paid_count = Loan.query.filter_by(status="Fully Paid").count()
    default_count = Loan.query.filter_by(status="Defaulted").count()

    # 5. Personal Member Data for Logged-In Officer (Wallet Modal)
    personal_savings = (
        Savings.query.filter_by(user_id=current_user.id)
        .order_by(Savings.date_recorded.desc())
        .all()
    )
    current_user_savings = sum(s.amount for s in personal_savings)

    # 6. All Global Transactions for All Members
    all_savings_transactions = (
        db.session.query(Savings, User)
        .join(User, Savings.user_id == User.id)
        .order_by(User.fname.asc(), Savings.date_recorded.desc())
        .all()
    )

    all_members = User.query.order_by(User.fname.asc()).all()

    all_fines_transactions = (
        db.session.query(FineFee, User)
        .join(User, FineFee.user_id == User.id)
        .order_by(User.fname.asc(), FineFee.date_recorded.desc())
        .all()
    )

    all_expenses_transactions = (
        db.session.query(Expense, User)
        .join(User, Expense.recorded_by == User.id)
        .order_by(User.fname.asc(), Expense.date_recorded.desc())
        .all()
    )

    return render_template(
        "finance/dashboard.html",
        total_savings=total_savings,
        unpaid_loans=unpaid_loans,
        membership_fees=membership_fees,
        total_fines_fees=total_fines_fees,
        loan_profits=loan_profits,
        performing_count=performing_count,
        fully_paid_count=fully_paid_count,
        default_count=default_count,
        top_savers=top_savers,
        all_loans=all_loans,
        savings=personal_savings,
        current_user_savings=current_user_savings,
        all_savings_transactions=all_savings_transactions,
        all_fines_transactions=all_fines_transactions,
        all_expenses_transactions=all_expenses_transactions,
        all_members=all_members,
        fy_labels=fy_labels,
        fy_disbursements=fy_disbursements,
        fy_repayments=fy_repayments,
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

@finance_bp.route('/savings/edit/<int:id>', methods=['POST'])
@login_required
def edit_savings(id):
    # Fixed the typo from is__bp to is_finance
    if not getattr(current_user, 'is_finance', False) and getattr(current_user, 'role', None) != 'finance':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('finance.dashboard')) # match your blueprint name here

    saving = Savings.query.get_or_404(id)
    
    new_deposit_type = request.form.get('deposit_type')
    new_amount = request.form.get('amount')

    try:
        saving.deposit_type = new_deposit_type
        saving.amount = float(new_amount)
        db.session.commit()
        flash('Savings record updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating record: {e}', 'danger')

    return redirect(url_for('finance.dashboard'))


@finance_bp.route('/savings/delete/<int:id>', methods=['POST'])
@login_required
def delete_savings(id):
    if not getattr(current_user, 'is_finance', False) and getattr(current_user, 'role', None) != 'finance':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('finance_bp.dashboard'))

    saving = Savings.query.get_or_404(id)

    try:
        db.session.delete(saving)
        db.session.commit()
        flash('Savings record deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting record: {e}', 'danger')

    return redirect(url_for('finance.dashboard'))

# ================= LOAN REPAYMENT EDIT & DELETE ROUTES =================

@finance_bp.route('/repayment/edit/<int:id>', methods=['POST'])
@login_required
def edit_loan_repayment(id):
    if current_user.role not in ['finance', 'treasurer', 'chair'] and not getattr(current_user, 'is_finance', False):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('finance.dashboard'))

    loan = Loan.query.get_or_404(id)
    new_amount = request.form.get('amount_repaid')

    try:
        loan.amount_repaid = float(new_amount)
        loan.check_and_update_status()
        db.session.commit()
        flash('Loan repayment record updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating repayment: {e}', 'danger')

    return redirect(url_for('finance.dashboard'))


@finance_bp.route('/repayment/delete/<int:id>', methods=['POST'])
@login_required
def delete_loan_repayment(id):
    if current_user.role not in ['finance', 'treasurer', 'chair'] and not getattr(current_user, 'is_finance', False):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('finance.dashboard'))

    loan = Loan.query.get_or_404(id)

    try:
        loan.amount_repaid = 0.0
        loan.check_and_update_status()
        db.session.commit()
        flash('Loan repayment contribution cleared successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing repayment: {e}', 'danger')

    return redirect(url_for('finance.dashboard'))


# ================= FINES & FEES EDIT & DELETE ROUTES =================

@finance_bp.route('/fine/edit/<int:id>', methods=['POST'])
@login_required
def edit_fine(id):
    if current_user.role not in ['finance', 'treasurer', 'chair'] and not getattr(current_user, 'is_finance', False):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('finance.dashboard'))

    fine = FineFee.query.get_or_404(id)
    new_fee_type = request.form.get('fee_type')
    new_amount = request.form.get('amount')
    new_status = request.form.get('status')

    try:
        fine.fee_type = new_fee_type
        fine.amount = float(new_amount)
        if new_status:
            fine.status = new_status
        db.session.commit()
        flash('Fine or fee record updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating fine/fee: {e}', 'danger')

    return redirect(url_for('finance.dashboard'))


@finance_bp.route('/fine/delete/<int:id>', methods=['POST'])
@login_required
def delete_fine(id):
    if current_user.role not in ['finance', 'treasurer', 'chair'] and not getattr(current_user, 'is_finance', False):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('finance.dashboard'))

    fine = FineFee.query.get_or_404(id)

    try:
        db.session.delete(fine)
        db.session.commit()
        flash('Fine or fee record deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting fine/fee: {e}', 'danger')

    return redirect(url_for('finance.dashboard'))