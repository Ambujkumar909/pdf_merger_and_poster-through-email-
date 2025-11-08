PDF Order Document Processor & Emailer
Tagline: Automate the consolidation of related order documents into a single PDF and deliver it instantly via email, using the file naming convention to personalize the subject line.

Key Features
Batch PDF Merging: Accepts up to 10 PDF files with a strict combined size limit of 15 MB.

Automatic Order ID Extraction: Scans uploaded filenames to automatically identify the document named using the Order ID.

Strict Rule: The Order ID must be 9 to 14 characters long and purely alphanumeric.

Dynamic Email Subject: Uses the extracted Order ID to generate a professional, context-specific email subject (e.g., Order Document: [ORDER_ID]).

Secure Email Dispatch: Sends the merged PDF as an attachment using the SMTP protocol (ideal for Gmail/Google Workspace via App Passwords).

Secure Credential Management: Uses .env files and the python-dotenv library to securely manage sensitive SMTP server details and login credentials, keeping them out of the source code.

Clean-up: Automatically handles temporary files, saving only the final merged PDF (if required for manual download) and ensuring the server remains tidy.

Technology Stack
Backend Framework: Python Flask

PDF Processing: PyMuPDF (fitz) for high-performance merging.

Email Handling: Python smtplib and email modules.

Security: python-dotenv

⚙️ Setup and Configuration
Prerequisites
Python 3.x installed.

A valid email account (e.g., Gmail) and the corresponding App Password for secure SMTP login.

Installation
Clone the repository:

Bash

git clone https://github.com/your-username/pdf_merger_with_email.git
cd pdf_merger_with_email
Install required libraries:

Bash

pip install -r requirements.txt
(Requires: Flask, PyMuPDF, python-dotenv, etc.)

SMTP Configuration (Crucial Step)
The application requires your SMTP credentials to send emails. You must create a file named .env in the root directory (next to app.py) and populate it with your actual settings:

Plaintext

# .env file content: Replace placeholders with your actual details

# Gmail Server Settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Your Gmail Address (Must be the sender and login user)
SMTP_USERNAME=your.actual.email@gmail.com
SENDER_EMAIL=your.actual.email@gmail.com

# Your 16-character Google App Password (NOT your regular account password)
SMTP_PASSWORD=abcd efgh ijkl mnop
Running the Application
Ensure the .env file is set up.

Run the Flask application:
python app.py
Access the web interface at the address provided in your console (usually http://127.0.0.1:5000/).

📌 Usage
Navigate to the main page (/).

Enter the Recipient Email Address.

Select all PDF files to be merged (max 10, max 15MB total). Ensure one file's base name matches the 9-14 alphanumeric Order ID format (e.g., ORD12345ABC.pdf).

Click "Merge Files & Send Email".

The system handles the file merging, ID extraction, and email dispatch, providing status feedback on the results page.
