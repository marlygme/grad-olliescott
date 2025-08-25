
# Legal & Compliance Pack for Gradvantage

This pack provides production-ready legal pages and compliance features for Australian user-generated content platforms.

## Files Created

### Core Legal Pages
- `/terms` - Australian Terms of Use with ACL compliance
- `/privacy` - Privacy Policy aligned with Australian Privacy Principles (APP)
- `/moderation` - Content moderation policy and takedown procedures
- `/report` - Content reporting form with webhook integration

### Configuration & Assets
- `legal_config.py` - Central configuration file with all placeholders
- `static/cookie-banner.js` - Cookie consent management
- `static/cookie-banner.css` - Cookie banner styling
- `public/robots.txt` - Search engine guidelines
- `public/.well-known/security.txt` - Security contact information

## Configuration Required

Edit `legal_config.py` to replace these placeholders:

```python
LEGAL_CONFIG = {
    'SITE_NAME': 'Gradvantage',
    'LEGAL_NAME': '{{Your Pty Ltd legal name}}',  # Replace with your company name
    'ABN': '{{Your ABN}}',                        # Your Australian Business Number
    'CONTACT_EMAIL': '{{legal@yourdomain.au}}',   # Legal contact email
    'POSTAL_ADDRESS': '{{Your mailing address}}', # Physical address for legal notices
    'REPORT_WEBHOOK_URL': '{{Your webhook URL}}', # Tally/Formspree/Make webhook
    'PRIVACY_OFFICER': '{{Name, role, email}}',   # Privacy officer details
}
```

## Report Webhook Integration

The report form submits JSON to your specified webhook URL:

```json
{
  "reporter_name": "John Doe",
  "reporter_email": "john@example.com",
  "content_url": "https://gradvantage.com/company/allens",
  "problematic_content": "Specific text being reported",
  "reason_for_report": "defamatory",
  "detailed_explanation": "Explanation of the issue",
  "supporting_evidence": "https://example.com/screenshot",
  "truth_declaration": true,
  "urgent_matter": false,
  "submitted_at": "2025-01-XX...",
  "site": "Gradvantage"
}
```

### Webhook Setup Options

**Tally Forms:**
1. Create a form with matching fields
2. Use Tally's webhook URL from form settings

**Formspree:**
1. Create a form at formspree.io
2. Use the provided endpoint URL

**Make.com/Zapier:**
1. Create a webhook trigger
2. Add email/Slack notifications
3. Store in database/spreadsheet

## Cookie Consent Features

- Essential cookies always allowed
- Analytics cookies require consent
- User preference storage in localStorage
- Google Analytics integration (when consented)
- Test IDs for automated testing

## Australian Legal Compliance

✅ **Australian Consumer Law (ACL)** - Non-excludable rights preserved
✅ **Privacy Act 1988** - APP-compliant privacy policy
✅ **Notifiable Data Breaches** - OAIC notification procedures
✅ **Defamation Law** - Clear takedown and appeal processes
✅ **Copyright Act** - DMCA-style notice and takedown

## Testing Checklist

- [ ] All legal pages load without errors
- [ ] Cookie banner appears on first visit
- [ ] Cookie preferences save correctly
- [ ] Report form submits to webhook
- [ ] Mobile layouts are readable
- [ ] All placeholders are visible and clearly marked
- [ ] Footer links work correctly

## Security Contact

Security vulnerabilities should be reported to the email specified in `CONTACT_EMAIL`. The security.txt file is automatically generated and placed at `/.well-known/security.txt`.

## Next Steps

1. Replace all placeholders in `legal_config.py`
2. Set up your report webhook service
3. Test the cookie banner functionality
4. Review all legal content with your lawyer
5. Add legal page links to your main navigation if desired

---

**Note:** This pack provides a solid foundation, but you should have all legal content reviewed by an Australian lawyer familiar with your specific business and industry requirements.
