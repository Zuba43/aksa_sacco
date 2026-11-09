from flask import Blueprint, render_template, redirect, url_for, flash, request,current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.routes.forms import LoginForm, RegistrationForm
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.login_id.data
        password = form.password.data
        
        # Check by username or phone
        user = User.query.filter((User.username == identifier) | (User.phone == identifier)).first()
        
        if user and user.check_password(password):
            if not user.is_active_account:
                flash('Your account is pending activation by the Secretary. Please check back later.', 'warning')
                return redirect(url_for('auth.login'))
                
            login_user(user, remember=form.remember.data)
            return redirect(url_for('dashboard.index'))
        
        flash('Invalid username/phone or password.', 'danger')
        
    return render_template('auth/login.html', form=form)

import os
from werkzeug.utils import secure_filename
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # 1. Check if email or username already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'warning')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'warning')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(phone=form.phone.data).first():
            flash('Phone number already registered.', 'warning')
            return redirect(url_for('auth.register'))

        # 2. Handle optional file uploads (Passport Photo & ID Scan)
        passport_filename = None
        if form.passport_photo.data:
            f = form.passport_photo.data
            passport_filename = secure_filename(f.filename)
            upload_folder = os.path.join(current_app.root_path, 'static/uploads/kyc')
            os.makedirs(upload_folder, exist_ok=True)
            f.save(os.path.join(upload_folder, passport_filename))

        id_scan_filename = None
        if form.id_scan.data:
            f = form.id_scan.data
            id_scan_filename = secure_filename(f.filename)
            upload_folder = os.path.join(current_app.root_path, 'static/uploads/kyc')
            os.makedirs(upload_folder, exist_ok=True)
            f.save(os.path.join(upload_folder, id_scan_filename))

        # 3. Create the new user instance with ALL fields mapped
        new_user = User(
            fname=form.fname.data,
            lname=form.lname.data,
            username=form.username.data,
            phone=form.phone.data,
            email=form.email.data,
            gender=form.gender.data,
            dob=form.dob.data,
            home_district=form.home_district.data,
            nin=form.nin.data,
            
            # KYC Documents
            passport_photo=passport_filename,
            id_scan=id_scan_filename,
            
            # Next of Kin & Emergency Contacts (3 Persons for SACCO Coverage)
            emergency_name_1=form.emergency_name_1.data,
            emergency_phone_1=form.emergency_phone_1.data,
            emergency_relation_1=form.emergency_relation_1.data,

            emergency_name_2=form.emergency_name_2.data,
            emergency_phone_2=form.emergency_phone_2.data,
            emergency_relation_2=form.emergency_relation_2.data,

            nok_name=form.nok_name.data,
            nok_phone=form.nok_phone.data,
            nok_relation=form.nok_relation.data,
            
            # Defaults
            role='member',
            is_active_account=False
        )
        
        # 4. Hash password and save to database
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Awaiting Secretary approval.', 'success')
        return redirect(url_for('auth.login'))
        
    elif request.method == 'POST':
        # Catches validation errors and flashes them to the user
        print("FORM VALIDATION FAILED:", form.errors)
        for field_name, errors in form.errors.items():
            field_label = getattr(form, field_name).label.text if hasattr(form, field_name) else field_name
            for error in errors:
                flash(f"{field_label}: {error}", "danger")

    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

