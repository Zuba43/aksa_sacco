from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User, Loan, Minute, Notification, Savings
from app import db
from sqlalchemy import or_

chair_bp = Blueprint('chair', __name__, url_prefix='/chair')

@chair_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'chair':
        flash('Access restricted to the Chairman.', 'danger')
        return redirect(url_for('auth.login'))

    total_members = User.query.count()
    pending_loans = Loan.query.filter_by(status='Pending').all()
    approved_loans = Loan.query.filter(Loan.status.in_(['Approved', 'Active'])).all()
    pending_activations = User.query.filter_by(is_active_account=False).count()
    active_defaulters = Loan.query.filter(Loan.status.in_(['Approved', 'Active', 'Defaulted'])).all()
    recent_minutes = Minute.query.order_by(Minute.meeting_date.desc()).all()

    # Fetch all members list for Chairman's Role Management table & modal
    all_members = User.query.order_by(User.fname.asc()).all()
    print("DEBUG: All members fetched ->", [u.username for u in all_members])

    # Personal member context for the Chairman
    personal_savings = Savings.query.filter_by(user_id=current_user.id).order_by(Savings.date_recorded.desc()).all()
    personal_loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.date_applied.desc()).all()
    current_user_savings = sum(s.amount for s in personal_savings)

    return render_template(
        'chair/dashboard.html',
        total_members=total_members,
        pending_loans=pending_loans,
        approved_loans=approved_loans,
        pending_activations=pending_activations,
        active_defaulters=active_defaulters,
        recent_minutes=recent_minutes,
        all_members=all_members,
        savings=personal_savings,
        loans=personal_loans,
        current_user_savings=current_user_savings
    )

# Executive Role Assignment / Promotion & Demotion by Chairman
@chair_bp.route('/member/update-role', methods=['POST'])
@login_required
def update_member_role():
    if current_user.role != 'chair':
        flash('Unauthorized action. Restricted to the Chairman.', 'danger')
        return redirect(url_for('auth.login'))

    user_id = request.form.get('user_id')
    new_role = request.form.get('new_role')
    valid_roles = ['member', 'secretary', 'treasurer', 'finance', 'chair']

    if new_role not in valid_roles:
        flash('Invalid role specified.', 'warning')
        return redirect(url_for('chair.dashboard'))

    target_user = User.query.get_or_404(user_id)

    # Prevent chair from demoting themselves accidentally
    if target_user.id == current_user.id:
        flash('You cannot alter your own Chairman status directly from this panel.', 'warning')
        return redirect(url_for('chair.dashboard'))

    try:
        old_role = target_user.role
        target_user.role = new_role
        
        # Notify user of role change
        notif = Notification(
            user_id=target_user.id,
            title="System Role Updated",
            message=f"Your SACCO role has been updated from {old_role.capitalize()} to {new_role.capitalize()} by the Chairman.",
            category="governance"
        )
        db.session.add(notif)
        db.session.commit()

        flash(f'Successfully updated {target_user.fname} {target_user.lname} to {new_role.capitalize()}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating role: {str(e)}', 'danger')

    return redirect(url_for('chair.dashboard'))

# Executive Loan Approval by Chairman
@chair_bp.route('/loan/approve/<int:loan_id>', methods=['POST'])
@login_required
def approve_loan(loan_id):
    if current_user.role != 'chair':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.login'))

    loan = Loan.query.get_or_404(loan_id)
    loan.status = 'Approved'
    
    # Notify borrower of approval
    notif = Notification(
        user_id=loan.user_id,
        title="Loan Approved by Chairman",
        message=f"Your loan request of UGX {loan.amount_requested:,.2f} has been approved by the SACCO Chairman.",
        category="loan"
    )
    db.session.add(notif)
    db.session.commit()

    flash(f'Loan request for UGX {loan.amount_requested:,.2f} approved successfully.', 'success')
    return redirect(url_for('chair.dashboard'))

# Executive Loan Rejection by Chairman
@chair_bp.route('/loan/reject/<int:loan_id>', methods=['POST'])
@login_required
def reject_loan(loan_id):
    if current_user.role != 'chair':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.login'))

    loan = Loan.query.get_or_404(loan_id)
    loan.status = 'Rejected'
    
    # Notify borrower of rejection
    notif = Notification(
        user_id=loan.user_id,
        title="Loan Request Rejected",
        message=f"Your loan request of UGX {loan.amount_requested:,.2f} was not approved after executive review.",
        category="loan"
    )
    db.session.add(notif)
    db.session.commit()

    flash(f'Loan request of UGX {loan.amount_requested:,.2f} rejected.', 'warning')
    return redirect(url_for('chair.dashboard'))