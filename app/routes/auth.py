from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from werkzeug.utils import secure_filename
from app.routes.forms import LoginForm, RegistrationForm
from app import db
import uuid
import os

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

        # Set upload folder to static/uploads/kyc to match project layout
        upload_dir = os.path.join(current_app.root_path, "static", "uploads", "kyc")
        os.makedirs(upload_dir, exist_ok=True)

        # 2. Handle optional file uploads (Passport Photo & ID Scan)
        passport_filename = None
        if form.passport_photo.data:
            f = form.passport_photo.data
            ext = f.filename.rsplit(".", 1)[1].lower() if "." in f.filename else "jpg"
            passport_filename = f"passport_{uuid.uuid4().hex[:8]}.{ext}"
            f.save(os.path.join(upload_dir, secure_filename(passport_filename)))

        id_scan_filename = None
        if form.id_scan.data:
            f = form.id_scan.data
            ext = f.filename.rsplit(".", 1)[1].lower() if "." in f.filename else "pdf"
            id_scan_filename = f"id_{uuid.uuid4().hex[:8]}.{ext}"
            f.save(os.path.join(upload_dir, secure_filename(id_scan_filename)))

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
            
            # Next of Kin & Emergency Contacts
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


ALLOWED_PHOTO_EXT = {"png", "jpg", "jpeg", "webp"}
ALLOWED_ID_EXT = {"pdf", "png", "jpg", "jpeg"}

def _allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


@auth_bp.route("/update-kyc-documents", methods=["POST"])
@login_required
def update_kyc_documents():
    passport_file = request.files.get("passport_photo")
    id_scan_file = request.files.get("id_scan")

    has_passport = passport_file and passport_file.filename.strip() != ""
    has_id_scan = id_scan_file and id_scan_file.filename.strip() != ""

    if not has_passport and not has_id_scan:
        flash("Please choose at least one file to upload.", "warning")
        return redirect(request.referrer or url_for("member.dashboard"))

    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "kyc")
    os.makedirs(upload_dir, exist_ok=True)

    try:
        if has_passport:
            if not _allowed_file(passport_file.filename, ALLOWED_PHOTO_EXT):
                flash("Invalid passport photo format. Use JPG, PNG, or WEBP.", "danger")
                return redirect(request.referrer or url_for("member.dashboard"))

            ext = passport_file.filename.rsplit(".", 1)[1].lower()
            new_photo_name = f"passport_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
            passport_file.save(os.path.join(upload_dir, secure_filename(new_photo_name)))

            # Remove old photo file if it exists
            if current_user.passport_photo:
                old_path = os.path.join(upload_dir, current_user.passport_photo)
                if os.path.exists(old_path):
                    os.remove(old_path)

            current_user.passport_photo = new_photo_name

        if has_id_scan:
            if not _allowed_file(id_scan_file.filename, ALLOWED_ID_EXT):
                flash("Invalid ID scan format. Use PDF, JPG, or PNG.", "danger")
                return redirect(request.referrer or url_for("member.dashboard"))

            ext = id_scan_file.filename.rsplit(".", 1)[1].lower()
            new_id_name = f"id_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
            id_scan_file.save(os.path.join(upload_dir, secure_filename(new_id_name)))

            # Remove old ID scan file if it exists
            if current_user.id_scan:
                old_path = os.path.join(upload_dir, current_user.id_scan)
                if os.path.exists(old_path):
                    os.remove(old_path)

            current_user.id_scan = new_id_name

        db.session.commit()
        flash("KYC documents updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to upload documents: {str(e)}", "danger")

    return redirect(request.referrer or url_for("member.dashboard"))