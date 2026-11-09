from flask import Blueprint, redirect, url_for, flash
from flask_login import login_required, current_user

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def index():
    # Route users based on their role
    if current_user.role == 'chair':
        return redirect(url_for('chair.dashboard'))
    elif current_user.role == 'secretary':
        return redirect(url_for('secretary.dashboard'))

    elif current_user.role == 'finance':
        return redirect(url_for('finance.dashboard'))
    else:
        return redirect(url_for('member.dashboard'))