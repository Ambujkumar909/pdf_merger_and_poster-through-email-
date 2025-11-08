import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import time
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, render_template, send_from_directory, flash
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF (used for merging)
import sys
# --- Configuration for Order Processor ---
MAX_COMBINED_SIZE_MB = 25
MAX_COMBINED_SIZE_BYTES = MAX_COMBINED_SIZE_MB * 1024 * 1024
MAX_FILE_COUNT = 15
load_dotenv()
# Email Configuration (***REPLACE THESE WITH YOUR ACTUAL DETAILS***)
# Note: You need a real SMTP service (e.g., Gmail, Outlook, SendGrid) credentials
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com') 
SMTP_PORT = int(os.getenv('SMTP_PORT', 587)) 
SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'user@example.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'app_password_not_set')
SENDER_EMAIL = os.getenv('SENDER_EMAIL', SMTP_USERNAME)
EMAIL_BODY_TEXT = (
    "Dear Customer,\n\n"
    "Please find your merged Order Document attached.\n\n"
    "This document consolidates all related files for your Order ID.\n\n"
    "Best regards,\n"
    "The System Team"
)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
# Set the max content length slightly higher than 15MB for robust handling
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 
app.secret_key = '46c7e0c9899d5b5485b4c7e72da034f7' 

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# --------------------------------------------------------------------
# --- CORE LOGIC FUNCTIONS ---
# --------------------------------------------------------------------


def merge_pdfs(pdf_list, output_path):
    """Merges a list of PDF files into a single output file using fitz (PyMuPDF)."""
    merged_document = fitz.open()
    for pdf in pdf_list:
        try:
            with fitz.open(pdf) as document:
                merged_document.insert_pdf(document)
        except Exception as e:
            # Clean up the partially created merged file if an error occurs
            if os.path.exists(output_path):
                os.remove(output_path)
            raise Exception(f"Failed to merge PDF: {os.path.basename(pdf)}. Error: {e}")
            
    merged_document.save(output_path)


def identify_order_id(filenames: list) -> str | None:
    """
    Identifies the Order ID from a list of filenames.
    It looks for the filename matching the pattern: [order_id].pdf.
    It returns the filename without the .pdf extension.
    """
    # Simple regex to capture the base name of a file ending in .pdf
    order_id_pattern = re.compile(r'^(.*)\.pdf$', re.IGNORECASE)
    
    for name in filenames:
        match = order_id_pattern.match(name)
        if match:
            order_id = match.group(1)
            # Simple check to filter out generic file names which are unlikely to be order IDs
            if order_id.lower() not in ['file', 'document', 'page', 'scan']: 
                # This returns the base filename as the Order ID
                return order_id
                
    return None


def send_email_with_attachment(recipient_email, subject, body, file_path, filename):
    """Sends an email with the merged PDF attachment."""
    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD]):
        return False, "Email configuration is incomplete. Cannot send email."

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # Attach the PDF
        with open(file_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {filename}',
        )
        msg.attach(part)

        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        
        return True, "Email sent successfully."
    except Exception as e:
        # Important for debugging: print or log the SMTP error
        print(f"SMTP Error: {e}")
        return False, f"Failed to send email. Check SMTP configuration and credentials. Error: {str(e)}"


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

# --------------------------------------------------------------------
# --- FLASK ROUTES ---
# --------------------------------------------------------------------


@app.route('/')
def index():
    """Renders the main upload form."""
    return render_template('process_order.html', max_size_mb=MAX_COMBINED_SIZE_MB, max_count=MAX_FILE_COUNT)


@app.route('/process', methods=['POST'])
def process_order_route():
    """Handles the merging, Order ID identification, and email sending."""
    recipient_email = request.form.get('email')
    files = request.files.getlist('files[]')
    
    if not recipient_email:
        flash('Please provide a recipient email address.', 'error')
        return redirect(url_for('index'))

    if not (1 <= len(files) <= MAX_FILE_COUNT):
        flash(f'Please select between 1 and {MAX_FILE_COUNT} PDF files.', 'error')
        return redirect(url_for('index'))
    
    pdf_list = []
    filenames_uploaded = []
    total_size = 0
    
    # 1. Validation and Temporary Save
    for file in files:
        if not (file and allowed_file(file.filename)):
            flash(f'Invalid file type found: {file.filename}. Only PDF files are allowed.', 'error')
            return redirect(url_for('index'))

        # Get file size and validate 15MB limit
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset pointer
        total_size += file_size
        
        if total_size > MAX_COMBINED_SIZE_BYTES:
            flash(f'Total file size ({total_size / (1024*1024):.2f} MB) exceeds the {MAX_COMBINED_SIZE_MB}MB limit.', 'error')
            return redirect(url_for('index'))

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        pdf_list.append(filepath)
        filenames_uploaded.append(filename)

    # 2. Identify Order ID & Prepare for Merge
    order_id = identify_order_id(filenames_uploaded)
    
    # Default to a timestamp if no clear Order ID is found
    if not order_id:
        order_id = f"MERGE-{int(time.time())}"
        flash(f'Could not automatically identify Order ID. Using **{order_id}** as the subject.', 'warning')
    
    subject = f"Order Id: {order_id}"
    merged_filename = f"{order_id}_Consolidated_Document.pdf"
    merged_pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], merged_filename)

    try:
        # 3. Merge PDFs
        merge_pdfs(pdf_list, merged_pdf_path)
        
        # 4. Send Email
        success, message = send_email_with_attachment(
            recipient_email,
            subject,
            EMAIL_BODY_TEXT,
            merged_pdf_path,
            merged_filename
        )

        # 5. Cleanup temporary uploaded files
        for path in pdf_list:
            os.remove(path)
        
        if success:
            flash(f'Success! Order ID: **{order_id}**. Files merged and emailed to {recipient_email}.', 'success')
            return render_template(
                'result.html',
                output_file=merged_filename,
                operation='process_order',
                email_sent=True
            )
        else:
            # Email failed: provide download link and keep merged file for manual action
            flash(f'Merge successful, but **EMAIL FAILED**: {message}', 'error')
            return render_template(
                'result.html',
                output_file=merged_filename,
                operation='process_order',
                email_sent=False
            )

    except Exception as e:
        # Cleanup uploaded files and remove partially merged file if it exists
        for path in pdf_list:
             if os.path.exists(path):
                 os.remove(path)
        if os.path.exists(merged_pdf_path):
             os.remove(merged_pdf_path)
             
        flash(f'A critical error occurred during processing: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/download/<filename>')
def download_file(filename):
    """Allows downloading the processed file from the outputs folder."""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)


if __name__ == "__main__":
    app.run(debug=True)
