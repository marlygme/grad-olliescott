# Overview

Gradvantage is a Flask-based web application that aggregates and displays graduate job experiences and insights for Australian law firms. The platform processes forum data (particularly from Whirlpool) and user submissions to provide structured information about clerkships, graduate programs, salaries, and application processes. The system includes data processing pipelines, content categorization, quality scoring, and experience filtering to deliver meaningful insights to law students and graduates.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Application Stack
- **Backend Framework**: Flask with Python 3.x
- **Template Engine**: Jinja2 for server-side rendering
- **Data Storage**: JSON files for submissions and application tracking
- **Frontend**: HTML/CSS with Bootstrap 5.3 and custom styling
- **Authentication**: Replit's ReplAuth system using HTTP headers

## Data Processing Pipeline
- **CSV Data Sources**: Multiple forum data files (law_raw.csv, law_whirlpool_2018_2025.csv, raw_all.csv)
- **Content Processing**: Multi-stage cleaning and filtering system to remove forum metadata
- **Quality Scoring**: Rule-based scoring system for experience quality and relevance
- **Content Categorization**: Automatic classification into 11 categories (application timeline, selection process, pay/benefits, etc.)
- **Firm Matching**: Alias-based system for mapping firm variations to canonical names

## Key Features
- **Experience Submission System**: Form-based user experience collection
- **Data-Assisted Drafting**: CSV-backed auto-population of experience forms
- **Company Analytics**: Aggregated firm statistics and program information
- **Content Filtering**: Answer-focused filtering excluding questions and low-quality posts
- **Legal Compliance**: Australian compliance pages for user-generated content platforms

## File Organization
```
├── main.py (Flask application)
├── submissions.json (user submissions)
├── applications.json (application tracking)
├── templates/ (Jinja2 templates)
├── static/ (CSS, JS assets)
├── extractors.py (firm aliases and data extraction)
├── categorizer.py (content classification)
├── experience_*.py (quality filtering pipelines)
├── grad_data*.py (CSV data processing)
├── legal_config.py (compliance configuration)
└── out/ (processed data outputs)
```

## Data Models
- **Submissions**: Company, role, experience type, application stages, interview experience, advice, salary data
- **Applications**: User application tracking with status, dates, and notes
- **Processed Experiences**: Cleaned forum posts with quality scores and categories
- **Firm Analytics**: Aggregated statistics including salary ranges, program types, and application timelines

# External Dependencies

## Required Python Packages
- **pandas**: Data manipulation and CSV processing
- **python-dateutil**: Date parsing and handling
- **pyarrow**: Parquet file support for data storage

## Authentication
- **Replit ReplAuth**: User authentication via HTTP headers (X-Replit-User-* headers)

## Frontend Libraries
- **Bootstrap 5.3**: CSS framework via CDN
- **Google Fonts**: Inter and Nunito font families
- **Custom CSS**: Additional styling for specialized components

## Data Sources
- **Forum CSVs**: Whirlpool forum data with thread titles, content, timestamps
- **User Submissions**: Direct form submissions via Flask routes
- **Legal Templates**: Australian compliance page templates

## Potential Future Integrations
- **Webhook Support**: Configured for Tally/Formspree/Make webhook integration
- **Analytics**: Google Analytics integration mentioned in legal config
- **External Services**: Airtable, Softr, Zapier/Make, Discord integrations planned