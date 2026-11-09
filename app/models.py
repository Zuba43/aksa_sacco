from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    
    # Credentials & Status
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Role & Account Activation (Pending until Secretary approves)
    role = db.Column(db.String(30), nullable=False, default='member')
    is_active_account = db.Column(db.Boolean, default=False) 
    
    # Bio Data
    fname = db.Column(db.String(50), nullable=False)
    lname = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    dob = db.Column(db.String(20), nullable=False)
    home_district = db.Column(db.String(50), nullable=False)
    nin = db.Column(db.String(30), unique=True, nullable=False)
    
    # KYC Documents (File paths/filenames)
    passport_photo = db.Column(db.String(255), nullable=True)
    id_scan = db.Column(db.String(255), nullable=True)
    
    # Next of Kin (NOK) Data
    emergency_name_1 = db.Column(db.String(100), nullable=False)
    emergency_phone_1 = db.Column(db.String(20), nullable=False)
    emergency_relation_1 = db.Column(db.String(50), nullable=False)

    # Emergency Contact 2
    emergency_name_2 = db.Column(db.String(100), nullable=False)
    emergency_phone_2 = db.Column(db.String(20), nullable=False)
    emergency_relation_2 = db.Column(db.String(50), nullable=False)

    # Emergency Contact 3 (Next of Kin)
    nok_name = db.Column(db.String(100), nullable=False)
    nok_phone = db.Column(db.String(20), nullable=False)
    nok_relation = db.Column(db.String(50), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    savings = db.relationship('Savings', backref='owner', lazy=True, cascade='all, delete-orphan')
    loans = db.relationship('Loan', back_populates='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} | Active: {self.is_active_account}>'


class Savings(db.Model):
    __tablename__ = 'savings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    deposit_type = db.Column(db.String(50), nullable=False, default='Monthly Share')
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)



# Add these classes to app/models.py

class Minute(db.Model):
    __tablename__ = 'minutes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    meeting_date = db.Column(db.String(30), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_attachment = db.Column(db.String(255), nullable=True) # Optional PDF upload path
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # None/Null = Broadcast to ALL members
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), default='general') # 'general', 'event', 'defaulter', 'reminder'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    


class Loan(db.Model):
    __tablename__ = 'loans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    loan_type = db.Column(db.String(20), nullable=False)
    amount_requested = db.Column(db.Float, nullable=False)
    tenure_months = db.Column(db.Integer, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    
    guarantor_name = db.Column(db.String(100), nullable=False)
    guarantor_email = db.Column(db.String(120), nullable=False)
    guarantor_phone = db.Column(db.String(20), nullable=False)
    
    date_applied = db.Column(db.DateTime, default=datetime.utcnow)

    # Use back_populates instead of backref
    user = db.relationship('User', back_populates='loans')
    amount_repaid = db.Column(db.Float, default=0.0)
    
class LoanRepayment(db.Model):
    __tablename__ = 'loan_repayments'

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_paid = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship back to loan
    loan = db.relationship('Loan', backref=db.backref('repayments', lazy=True, cascade='all, delete-orphan'))