import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import User, Loan, Minute, Notification, Savings
from app import db

secretary_bp = Blueprint('secretary', __name__, url_prefix='/secretary')

@secretary_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'secretary':
        flash('Access restricted to the Secretary.', 'danger')
        return redirect(url_for('auth.login'))

    # Fetch pending and active members matching the standard is_active_account column
    pending_members = User.query.filter_by(is_active_account=False).all()
    active_members = User.query.filter_by(is_active_account=True).all()
    recent_minutes = Minute.query.order_by(Minute.meeting_date.desc()).all()
    defaulter_loans = Loan.query.filter_by(status='Defaulted').all()

    # Personal member context for the logged-in Secretary
    personal_savings = Savings.query.filter_by(user_id=current_user.id).order_by(Savings.date_recorded.desc()).all()
    personal_loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.date_applied.desc()).all()
    current_user_savings = sum(s.amount for s in personal_savings)

    return render_template(
        'secretary/dashboard.html',
        pending_members=pending_members,
        active_members=active_members,
        recent_minutes=recent_minutes,
        defaulter_loans=defaulter_loans,
        savings=personal_savings,
        loans=personal_loans,
        current_user_savings=current_user_savings
    )


# Activate / Approve Account
@secretary_bp.route('/activate/<int:user_id>', methods=['POST'])
@login_required
def activate_member(user_id):
    if current_user.role not in ['secretary', 'chair']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.login'))

    member = User.query.get_or_404(user_id)
    member.is_active_account = True  # Updated from is_active_account to sync with query filter
    
    # Send a welcome notification to the member's portal
    welcome_note = Notification(
        user_id=member.id,
        title="Account Activated",
        message="Your AKSA SACCO membership has been reviewed and approved by the Secretary. Welcome!",
        category="general"
    )
    db.session.add(welcome_note)
    db.session.commit()

    flash(f'Account for {member.fname} {member.lname} ({member.username}) activated successfully!', 'success')
    return redirect(url_for('secretary.dashboard'))


# Reject / Delete Pending Application
@secretary_bp.route('/member/reject/<int:user_id>', methods=['POST'])
@login_required
def reject_member(user_id):
    if current_user.role not in ['secretary', 'chair']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.login'))
        
    user = User.query.get_or_404(user_id)
    name = f"{user.fname} {user.lname}"
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Membership application for {name} has been rejected and removed.', 'warning')
    return redirect(url_for('secretary.dashboard'))


# Deactivate / Suspend Account
@secretary_bp.route('/deactivate/<int:user_id>', methods=['POST'])
@login_required
def deactivate_member(user_id):
    if current_user.role not in ['secretary', 'chair']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.login'))

    member = User.query.get_or_404(user_id)
    member.is_active_account = False  # Updated from is_active_account to sync with query filter
    
    db.session.commit()

    flash(f'Account for {member.fname} {member.lname} has been deactivated.', 'warning')
    return redirect(url_for('secretary.dashboard'))


# Broadcast Notification (Events / General Announcements to All Members)
@secretary_bp.route('/send-broadcast', methods=['POST'])
@login_required
def send_broadcast():
    if current_user.role not in ['secretary', 'chair']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.login'))

    title = request.form.get('title')
    message = request.form.get('message')
    category = request.form.get('category', 'event')

    # user_id=None signifies a broadcast for all members
    new_notif = Notification(user_id=None, title=title, message=message, category=category)
    db.session.add(new_notif)
    db.session.commit()

    flash('Notification broadcasted to all member dashboards successfully!', 'success')
    return redirect(url_for('secretary.dashboard'))


# Send Direct Defaulter Reminder
@secretary_bp.route('/send-reminder/<int:user_id>', methods=['POST'])
@login_required
def send_reminder(user_id):
    if current_user.role not in ['secretary', 'chair']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.login'))

    message = request.form.get('message')
    reminder = Notification(
        user_id=user_id,
        title="Loan Payment Reminder",
        message=message or "This is a reminder from the Secretary to settle your overdue loan payment.",
        category="defaulter"
    )
    db.session.add(reminder)
    db.session.commit()

    flash('Defaulter reminder notification sent.', 'info')
    return redirect(url_for('secretary.dashboard'))


# Record Meeting Minutes
@secretary_bp.route('/record-minutes', methods=['POST'])
@login_required
def record_minutes():
    if current_user.role not in ['secretary', 'chair']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.login'))

    title = request.form.get('title')
    meeting_date = request.form.get('meeting_date')
    content = request.form.get('content')
    file = request.files.get('file_attachment')

    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(current_app.root_path, 'static/uploads/minutes')
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))

    new_minute = Minute(title=title, meeting_date=meeting_date, content=content, file_attachment=filename)
    db.session.add(new_minute)
    db.session.commit()

    flash('Meeting minutes published successfully.', 'success')
    return redirect(url_for('secretary.dashboard'))