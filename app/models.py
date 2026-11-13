from datetime import datetime
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from sqlalchemy import event
from sqlalchemy.orm import Session


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 1. Define the AuditLog model first using Flask-SQLAlchemy's db.Model
class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True, index=True)
    model_name = db.Column(db.String(50), nullable=False, index=True)
    record_id = db.Column(db.Integer, nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False, default="DELETE")
    deleted_data = db.Column(db.JSON, nullable=False)
    deleted_by = db.Column(db.String(100), nullable=True)
    deleted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # Credentials & Status
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Role & Account Activation (Pending until Secretary approves)
    role = db.Column(db.String(30), nullable=False, default="member")
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
    is_outsider = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    savings = db.relationship(
        "Savings", backref="owner", lazy=True, cascade="all, delete-orphan"
    )
    loans = db.relationship("Loan", back_populates="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} | Active: {self.is_active_account}>"


class Savings(db.Model):
    __tablename__ = "savings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    deposit_type = db.Column(db.String(50), nullable=False, default="Monthly Share")
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)
    friday_date = db.Column(db.Date, nullable=True)
    custom_months = db.Column(db.String(100), nullable=True)


class Minute(db.Model):
    __tablename__ = "minutes"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    meeting_date = db.Column(db.String(30), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_attachment = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )  # None/Null = Broadcast to ALL members
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(
        db.String(30), default="general"
    )  # 'general', 'event', 'defaulter', 'reminder'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Loan(db.Model):
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    loan_type = db.Column(db.String(20), nullable=False)
    amount_requested = db.Column(db.Float, nullable=False)
    tenure_months = db.Column(db.Integer, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Pending")

    guarantor_name = db.Column(db.String(100), nullable=False)
    guarantor_email = db.Column(db.String(120), nullable=False)
    guarantor_phone = db.Column(db.String(20), nullable=False)

    date_applied = db.Column(db.DateTime, default=datetime.utcnow)
    amount_repaid = db.Column(db.Float, default=0.0)

    user = db.relationship("User", back_populates="loans")

    @property
    def total_due(self):
        return self.amount_requested * (1.0 + (self.interest_rate / 100.0))

    @property
    def total_repaid(self):
        return self.amount_repaid or 0.0

    @property
    def balance_remaining(self):
        return max(0.0, self.total_due - self.total_repaid)

    def check_and_update_status(self):
        if self.status in ["Fully Paid", "Rejected", "Pending"]:
            return self.status

        now = datetime.utcnow()
        delta_days = (now - self.date_applied).days

        if self.balance_remaining <= 0:
            self.status = "Fully Paid"
        elif self.status in ["Approved", "Active"] and delta_days >= 90:
            self.status = "Defaulted"
        elif self.status == "Approved" and self.amount_repaid > 0:
            self.status = "Active"

        return self.status


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False, default="Administrative")
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[recorded_by])


class FineFee(db.Model):
    __tablename__ = "fines_fees"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    fee_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Unpaid")
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id])


# ==========================================
# UNIVERSAL DELETE AUDIT EVENT LISTENER
# ==========================================


def model_to_dict(model_instance):
  return {
      column.name: getattr(model_instance, column.name)
      for column in model_instance.__table__.columns
  }


def generic_audit_delete_listener(mapper, connection, target):
  # Skip auditing the AuditLog table itself if it ever gets deleted
  if isinstance(target, AuditLog):
    return

  session = Session.object_session(target)
  if not session:
    return

  model_name = target.__class__.__name__
  record_id = getattr(target, "id", None)
  row_data = model_to_dict(target)

  # Convert datetime/date objects to strings for JSON compatibility
  for key, value in row_data.items():
    if hasattr(value, "isoformat"):
      row_data[key] = value.isoformat()

  # Safely extract who performed the deletion using Flask-Login context if available
  deleted_by_user = "system"
  try:
    if current_user and current_user.is_authenticated:
      deleted_by_user = getattr(current_user, "username", str(current_user.id))
  except Exception:
    pass

  # Create the AuditLog model instance and add it directly to the active session
  audit_entry = AuditLog(
      model_name=model_name,
      record_id=record_id,
      action="DELETE",
      deleted_data=row_data,
      deleted_by=deleted_by_user,
      deleted_at=datetime.utcnow(),
  )

  session.add(audit_entry)


# CRITICAL FIX: propagate=True ensures this listens to ALL models inheriting from db.Model
event.listen(
    db.Model, "before_delete", generic_audit_delete_listener, propagate=True
)