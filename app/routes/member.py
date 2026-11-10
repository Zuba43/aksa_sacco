from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Savings, Loan, LoanRepayment, Notification, Minute,FineFee
from app import db
from app.utils import send_guarantor_notification
from datetime import datetime
member_bp = Blueprint('member', __name__, url_prefix='/member')

from sqlalchemy import desc

@member_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_active_account:
        flash('Your account is pending activation by the Secretary.', 'warning')
        return redirect(url_for('auth.login'))

    # Fetch user personal savings
    user_savings = Savings.query.filter_by(user_id=current_user.id).order_by(Savings.date_recorded.desc()).all()
    total_savings = sum(s.amount for s in user_savings)
    
    projected_profit = total_savings * 0.05

    # Fetch User Loans and attach computed balance: (Principal + 10% Interest) - Total Repaid
    user_loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.date_applied.desc()).all()
    for l in user_loans:
        # Sum all repayments for this specific loan
        repaid_sum = sum(r.amount for r in l.repayments) if hasattr(l, 'repayments') and l.repayments else 0.0
        # Total due = Principal + 10% interest
        total_due = l.amount_requested * 1.10
        # Store dynamic balance attribute on the loan object
        l.balance_remaining = max(0.0, total_due - repaid_sum)
        l.repaid_sum = repaid_sum
        l.total_due = total_due

    # Fetch recent transactions (Fines/Fees & Loan Repayments) for member activity tracking
    user_fines = FineFee.query.filter_by(user_id=current_user.id).all()
    
    # Extract repayments associated with user loans
    user_repayments = []
    for l in user_loans:
        if hasattr(l, 'repayments') and l.repayments:
            user_repayments.extend(l.repayments)

    # Combine into a unified history list and sort by date descending
    recent_activity = []
    for f in user_fines:
        recent_activity.append({
            'type': f'Fee/Fine: {f.fee_type}',
            'amount': f.amount,
            'date': f.date_recorded,
            'badge': 'bg-warning text-dark',
            'is_credit': False
        })
    for r in user_repayments:
        recent_activity.append({
            'type': f'Loan Repayment (Loan #{r.loan_id})',
            'amount': r.amount,
            'date': r.date_paid,
            'badge': 'bg-success text-white',
            'is_credit': True
        })

    # Sort combined activity by date and pick recent 5
    recent_transactions = sorted(
        recent_activity, 
        key=lambda x: x['date'] if x['date'] else datetime.min, 
        reverse=True
    )[:5]

    notifications = Notification.query.filter(
        (Notification.user_id == current_user.id) | (Notification.user_id == None)
    ).order_by(Notification.created_at.desc()).all()

    recent_minutes = Minute.query.order_by(Minute.created_at.desc()).limit(5).all()

    return render_template(
        'member/dashboard.html',
        savings=user_savings,
        total_savings=total_savings,
        projected_profit=projected_profit,
        loans=user_loans,
        recent_transactions=recent_transactions,
        notifications=notifications,
        recent_minutes=recent_minutes
    )

# Handle Friday Savings Entry Request
@member_bp.route('/save-friday', methods=['POST'])
@login_required
def save_friday():
    amount = float(request.form.get('amount', 0))
    
    # Weekly limit rule: 2,000 to 20,000 UGX
    if amount < 2000 or amount > 20000:
        flash('Friday weekly savings must be between UGX 2,000 and UGX 20,000.', 'danger')
        return redirect(url_for('member.dashboard'))

    new_savings = Savings(
        user_id=current_user.id,
        amount=amount,
        deposit_type='Friday Weekly Contribution'
    )
    db.session.add(new_savings)
    db.session.commit()

    flash(f'Successfully recorded Friday deposit of UGX {amount:,.2f}!', 'success')
    return redirect(url_for('member.dashboard'))

# Handle Loan Application Request with Guarantor and Loan Type Support
@member_bp.route('/apply-loan', methods=['POST'])
@login_required
def apply_loan():
    loan_type = request.form.get('loan_type', 'general')
    amount_requested = float(request.form.get('amount_requested', 0))
    tenure_months = int(request.form.get('tenure_months', 1))
    
    guarantor_name = request.form.get('guarantor_name', '').strip()
    guarantor_email = request.form.get('guarantor_email', '').strip()
    guarantor_phone = request.form.get('guarantor_phone', '').strip()

    # Basic validations
    if not all([guarantor_name, guarantor_email, guarantor_phone]):
        flash("All guarantor fields are required.", "danger")
        return redirect(url_for('member.dashboard'))

    if amount_requested < 50000:
        flash("Minimum loan amount is UGX 50,000.", "warning")
        return redirect(url_for('member.dashboard'))

    # Business Rule Adjustments
    if loan_type == 'emergency':
        interest_rate = 7.0
        tenure_months = 1  # Force 1 month for emergency loans
    else:
        interest_rate = 10.0
        if tenure_months > 3:
            tenure_months = 3  # Max 3 months for general loans

    try:
        new_loan = Loan(
            user_id=current_user.id,
            loan_type=loan_type,
            amount_requested=amount_requested,
            tenure_months=tenure_months,
            interest_rate=interest_rate,
            guarantor_name=guarantor_name,
            guarantor_email=guarantor_email,
            guarantor_phone=guarantor_phone,
            status='Pending'
        )
        
        db.session.add(new_loan)
        db.session.commit()

        # Send email to guarantor
        try:
            send_guarantor_notification(new_loan, current_user)
            flash("Loan application submitted successfully. Guarantor notified via email.", "success")
        except Exception as mail_err:
            # Fallback if mail fails so transaction doesn't revert unnecessarily
            flash("Loan application submitted, but failed to send guarantor email notification.", "warning")

    except Exception as e:
        db.session.rollback()
        flash("An error occurred while submitting your application. Please try again.", "danger")

    return redirect(url_for('member.dashboard'))

from app.models import Savings, Loan, LoanRepayment, Notification, Minute
@member_bp.route('/repay-loan', methods=['POST'])
@login_required
def repay_loan():
    loan_id = request.form.get('loan_id', type=int)
    repayment_amount = float(request.form.get('repayment_amount', 0))

    if not loan_id or repayment_amount <= 0:
        flash("Invalid repayment details provided.", "danger")
        return redirect(url_for('member.dashboard'))

    loan = Loan.query.filter_by(id=loan_id, user_id=current_user.id).first()

    if not loan:
        flash("Loan record not found.", "danger")
        return redirect(url_for('member.dashboard'))

    if loan.status != 'Approved':
        flash("Repayments can only be made against approved active loans.", "warning")
        return redirect(url_for('member.dashboard'))

    try:
        # Record the individual repayment transaction with its date
        new_repayment = LoanRepayment(
            loan_id=loan.id,
            amount=repayment_amount
        )
        db.session.add(new_repayment)

        # Calculate total amount paid so far
        total_paid_so_far = sum(r.amount for r in loan.repayments) + repayment_amount
        
        # Calculate total due (Principal + Interest)
        total_due = loan.amount_requested * (1 + (loan.interest_rate / 100))

        if total_paid_so_far >= total_due:
            loan.status = 'Paid'
            flash(f"Repayment of UGX {repayment_amount:,.2f} recorded! Loan #{loan.id} has been fully settled.", "success")
        else:
            remaining = total_due - total_paid_so_far
            flash(f"Repayment of UGX {repayment_amount:,.2f} recorded successfully. Remaining balance: UGX {remaining:,.2f}.", "success")

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        flash("An error occurred while processing your repayment. Please try again.", "danger")

    return redirect(url_for('member.dashboard'))

