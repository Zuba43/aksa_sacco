from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Savings, Loan, Notification, Minute, FineFee
from app import db
from app.utils import send_guarantor_notification
from datetime import datetime, timedelta

member_bp = Blueprint('member', __name__, url_prefix='/member')
@member_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_active_account:
        flash('Your account is pending activation by the Secretary.', 'warning')
        return redirect(url_for('auth.login'))

    user_savings = Savings.query.filter_by(user_id=current_user.id).order_by(Savings.date_recorded.desc()).all()
    total_savings = sum(s.amount for s in user_savings)
    projected_profit = total_savings * 0.05

    user_loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.date_applied.desc()).all()
    
    # Automatically evaluate statuses
    status_updated = False
    for loan in user_loans:
        old_status = loan.status
        loan.check_and_update_status()
        if loan.status != old_status:
            status_updated = True

    if status_updated:
        db.session.commit()

    notifications = Notification.query.filter(
        (Notification.user_id == current_user.id) | (Notification.user_id == None)
    ).order_by(Notification.created_at.desc()).all()

    recent_minutes = Minute.query.order_by(Minute.created_at.desc()).limit(5).all()
    
    fines_fees = FineFee.query.filter_by(user_id=current_user.id).all()

    recent_transactions = []
    for ff in fines_fees:
        recent_transactions.append({
            'date': ff.date_recorded,
            'type': f"Fine/Fee: {ff.fee_type}",
            'amount': ff.amount,
            'is_credit': False,
            'badge': 'bg-danger' if ff.status == 'Unpaid' else 'bg-secondary'
        })

    recent_transactions.sort(key=lambda x: x['date'] if x['date'] else datetime.min, reverse=True)
    recent_transactions = recent_transactions[:5]

    return render_template(
        'member/dashboard.html',
        savings=user_savings,
        total_savings=total_savings,
        projected_profit=projected_profit,
        loans=user_loans,
        notifications=notifications,
        recent_minutes=recent_minutes,
        recent_transactions=recent_transactions
    )


from datetime import datetime

@member_bp.route('/save-friday', methods=['POST'])
@login_required
def save_friday():
    amount = float(request.form.get('amount', 0))
    saving_period = request.form.get('saving_period', 'friday')
    
    parsed_friday_date = None
    custom_months_str = None
    period_label = "Savings Deposit"
    
    min_limit = 2000
    max_limit = 25000

    if saving_period == 'friday':
        friday_date_str = request.form.get('friday_date')
        if not friday_date_str:
            flash('Please select a valid Friday date from the calendar.', 'danger')
            return redirect(url_for('member.dashboard'))
        
        try:
            parsed_friday_date = datetime.strptime(friday_date_str, '%Y-%m-%d').date()
            if parsed_friday_date.weekday() != 4:
                flash('Selected date must be a Friday.', 'danger')
                return redirect(url_for('member.dashboard'))
        except ValueError:
            flash('Invalid date format received.', 'danger')
            return redirect(url_for('member.dashboard'))
            
        period_label = f"Friday Weekly ({parsed_friday_date.strftime('%d %b %Y')})"
        min_limit = 2000
        max_limit = 25000

    elif saving_period == 'custom':
        custom_months_list = request.form.getlist('custom_months')
        if not custom_months_list:
            flash('Please select at least one month for custom savings.', 'danger')
            return redirect(url_for('member.dashboard'))
        
        custom_months_str = ", ".join(custom_months_list)
        month_count = len(custom_months_list)
        
        min_limit = 8000 * month_count
        max_limit = 125000 * month_count
        period_label = f"Custom Savings ({custom_months_str})"

    # Validate amount against the calculated limits
    if amount < min_limit or amount > max_limit:
        flash(f'Contributions for {period_label.lower()} must be between UGX {min_limit:,.0f} and UGX {max_limit:,.0f}.', 'danger')
        return redirect(url_for('member.dashboard'))

    # Save to database
    new_savings = Savings(
        user_id=current_user.id,
        amount=amount,
        deposit_type=period_label,
        friday_date=parsed_friday_date,
        custom_months=custom_months_str
    )
    db.session.add(new_savings)
    db.session.commit()

    flash(f'Successfully recorded deposit of UGX {amount:,.2f} ({period_label})!', 'success')
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
            flash("Loan application submitted, but failed to send guarantor email notification.", "warning")

    except Exception as e:
        db.session.rollback()
        flash("An error occurred while submitting your application. Please try again.", "danger")

    return redirect(url_for('member.dashboard'))

@member_bp.route('/repay-loan', methods=['POST'])
@login_required
def repay_loan():
    loan_id = request.form.get('loan_id', type=int)
    repayment_amount = float(request.form.get('repayment_amount', 0))

    if not loan_id or repayment_amount <= 0:
        flash("Invalid repayment details provided.", "danger")
        return redirect(request.referrer or url_for('member.dashboard'))

    # Allow finance/treasurers or the loan owner to submit payments
    loan = Loan.query.filter_by(id=loan_id).first()

    if not loan:
        flash("Loan record not found.", "danger")
        return redirect(request.referrer or url_for('member.dashboard'))

    if loan.status not in ['Approved', 'Active', 'Defaulted']:
        flash("Repayments can only be made against active, approved, or at-risk loans.", "warning")
        return redirect(request.referrer or url_for('member.dashboard'))

    try:
        # Increment amount repaid directly
        loan.amount_repaid = (loan.amount_repaid or 0.0) + repayment_amount
        total_due = loan.total_due

        # Update status check
        if loan.amount_repaid >= total_due:
            loan.status = 'Fully Paid'
            flash(f"Repayment of UGX {repayment_amount:,.2f} recorded! Loan #{loan.id} is now fully settled.", "success")
        else:
            loan.status = 'Active'  
            remaining = loan.balance_remaining
            flash(f"Repayment of UGX {repayment_amount:,.2f} recorded. Remaining balance: UGX {remaining:,.2f}.", "success")

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while processing your repayment: {str(e)}", "danger")

    # Redirect back to whichever dashboard the officer was on (finance or member)
    return redirect(request.referrer or url_for('member.dashboard'))

