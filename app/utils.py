from flask import render_template
from flask_mail import Message
from app import mail

def send_guarantor_notification(loan, applicant):
    subject = f"AKSA SACCO - Guarantee Obligation Notice for {applicant.fname} {applicant.lname}"
    
    # Email body detailing obligations
    body = f"""
Dear {loan.guarantor_name},

This is an automated notification from AKSA SACCO.

{applicant.fname} {applicant.lname} ({applicant.phone}) has submitted a loan application and designated you as their official Guarantor.

LOAN DETAILS:
------------------------------------------
Loan Type: {loan.loan_type.capitalize()} Loan
Requested Amount: UGX {loan.amount_requested:,.2f}
Tenure: {loan.tenure_months} Month(s)
Interest Rate: {loan.interest_rate}%

GUARANTOR OBLIGATION DISCLAIMER:
By being designated as a guarantor, you agree to ensure the prompt repayment of this loan. 
{"Note: This Emergency Loan carries a strict 1-month repayment term. Failure to repay within 1 month increases the rate to 12%." if loan.loan_type == 'emergency' else ""}

If you did not authorize this or have any concerns, please contact AKSA SACCO management immediately.

Best regards,
AKSA SACCO Management Team
"""
    
    msg = Message(
        subject=subject,
        recipients=[loan.guarantor_email],
        body=body,
        sender="noreply@aksasacco.com"
    )
    
    mail.send(msg)