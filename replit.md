# Overview

GradGuide is a graduate job insights platform for Australian law firms. The application has been restructured for Cloudflare Pages deployment, with a **static frontend** and **separate JSON API backend**. The platform provides structured information about clerkships, graduate programs, salaries, and application processes from user-submitted experiences.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Current Stack (Cloudflare Pages Ready)
- **Frontend**: Static HTML/CSS/JavaScript in `public/` folder
- **Backend API**: Flask serving JSON endpoints from `api.py`
- **Data Storage**: JSON files for submissions (can be replaced with database)
- **CSS Framework**: Bootstrap 5.3 with custom Inter font styling
- **Authentication**: Replit headers (X-Replit-User-Id, X-Replit-User-Name)

## Static Frontend Structure
```
public/
├── index.html          # Homepage
├── companies.html      # Companies listing
├── company.html        # Company detail page
├── experiences.html    # Experiences listing
├── tracker.html        # Application tracker
├── law-match.html      # Career match tool
├── submit.html         # Submit experience form
├── terms.html          # Terms of use
├── privacy.html        # Privacy policy
├── moderation.html     # Content policy
├── report.html         # Report content
├── css/
│   ├── style.css           # Main styles
│   └── cookie-banner.css   # Cookie consent styles
└── js/
    ├── api.js              # API service module
    ├── app.js              # App utilities
    └── cookie-banner.js    # Cookie consent logic
```

## API Endpoints
- `GET /api/companies` - List all companies with stats
- `GET /api/companies/<name>` - Get company details and experiences
- `GET /api/experiences` - List all experiences (with filters)
- `POST /api/experiences` - Submit new experience
- `GET /api/user` - Get current user (via headers)
- `GET/POST/PUT/DELETE /api/applications` - Application tracker CRUD
- `GET /api/firm-university-data` - Firm university representation data
- `POST /api/law-match` - Get firm recommendations

## Key Features
- **Experience Submission System**: Form-based user experience collection
- **Company Analytics**: Aggregated firm statistics and program information
- **Application Tracker**: Personal job application tracking
- **Career Match Tool**: University-based firm recommendations
- **GDPR Compliance**: Cookie consent banner

## Data Models
- **Submissions**: Company, role, experience type, application stages, interview experience, advice
- **Applications**: User application tracking with status, dates, and notes
- **Firm Analytics**: University representation percentages for career matching

# Deployment Notes

## For Cloudflare Pages
1. Deploy the `public/` folder as the static site
2. Set up API backend separately (Workers, external server, etc.)
3. Configure `API_BASE_URL` in the frontend JS to point to your API

## For Development (Replit)
- Run `python api.py` to serve both static files and API from port 5000
- The Flask server serves static files from `public/` directory

# External Dependencies

## Python Packages
- Flask
- Flask-CORS
- gunicorn (for production)

## Frontend Libraries (CDN)
- Bootstrap 5.3
- Bootstrap Icons
- Inter font (Google Fonts)
