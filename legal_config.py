
"""
Legal & Compliance Configuration for Gradvantage
Edit these placeholders to match your business details
"""

from datetime import datetime

LEGAL_CONFIG = {
    'SITE_NAME': 'GradGuide',
    'LEGAL_NAME': '{{Your Pty Ltd legal name}}',
    'ABN': '{{Your ABN}}',
    'CONTACT_EMAIL': '{{legal@yourdomain.au}}',
    'POSTAL_ADDRESS': '{{Your mailing address}}',
    'GOVERNING_LAW': 'Victoria, Australia',
    'PROCESSORS': [
        'Airtable', 'Softr', 'Tally', 'Zapier/Make', 
        'Google Analytics', 'Discord', 'Replit'
    ],
    'REPORT_WEBHOOK_URL': '{{Your Tally/Formspree/Make webhook}}',
    'PRIVACY_OFFICER': '{{Name, role, email}}',
    'LAST_UPDATED': datetime.now().strftime('%d %B %Y')
}

# Not Advice Disclaimer
NOT_ADVICE_DISCLAIMER = f"{LEGAL_CONFIG['SITE_NAME']} provides general information and user-submitted content. We don't provide legal, financial or career advice. Consider your circumstances and seek professional advice before acting."
