
import re
import pandas as pd
from datetime import datetime
from rapidfuzz import fuzz
import pytz
from dateutil import parser as date_parser

# Firm dictionary with aliases
FIRM_ALIASES = {
    "Clayton Utz": ["clayton utz", "clutz", "claytons"],
    "Allens": ["allens"],
    "Herbert Smith Freehills": ["herbert smith freehills", "hsf", "herbies"],
    "Ashurst": ["ashurst"],
    "MinterEllison": ["minterellison", "minter ellison", "minters"],
    "Colin Biggers & Paisley": ["colin biggers", "cbp", "cb&p"],
    "Lander & Rogers": ["lander & rogers", "landers"],
    "Addisons": ["addisons"],
    "Clifford Chance": ["clifford chance", "cc"],
    "King & Wood Mallesons": ["king & wood mallesons", "kwm", "mallesons"],
    "Corrs Chambers Westgarth": ["corrs", "corrs chambers"],
    "Gilbert + Tobin": ["gilbert + tobin", "g+t", "gtobin", "g+tobin"],
    "HWL Ebsworth": ["hwl", "hwl ebsworth"],
    "Maddocks": ["maddocks"],
    "Sparke Helmore": ["sparke helmore", "sparke"],
    "Hall & Wilcox": ["hall & wilcox", "h&w"],
    "Baker McKenzie": ["baker mckenzie", "bakers"],
    "Norton Rose Fulbright": ["norton rose fulbright", "nrf"],
    "DLA Piper": ["dla piper", "dla"],
    "White & Case": ["white & case", "w&c"],
    "Johnson Winter Slattery": ["johnson winter slattery", "jws"],
    "Thomson Geer": ["thomson geer"],
    "HFW": ["hfw"],
    "Bird & Bird": ["bird & bird", "b&b"],
    "McCullough Robertson": ["mccullough robertson", "mccullough"],
    "Turks Legal": ["turks legal"],
    "Barry Nilsson": ["barry nilsson"]
}

class FirmMatcher:
    def __init__(self):
        self.firm_aliases = FIRM_ALIASES
        
    def find_firms(self, text):
        """Find firm matches in text, returning (firm_name, alias, start, end) tuples"""
        matches = []
        text_lower = text.lower()
        
        for firm_name, aliases in self.firm_aliases.items():
            # Check exact alias matches first
            for alias in aliases:
                start_idx = 0
                while True:
                    idx = text_lower.find(alias, start_idx)
                    if idx == -1:
                        break
                    
                    # Check word boundaries
                    if self._is_word_boundary(text_lower, idx, idx + len(alias)):
                        matches.append((firm_name, alias, idx, idx + len(alias)))
                    
                    start_idx = idx + 1
            
            # Fuzzy matching as backup for firm names not found exactly
            if not any(match[0] == firm_name for match in matches):
                fuzzy_matches = self._fuzzy_match(text_lower, firm_name)
                matches.extend(fuzzy_matches)
        
        return matches
    
    def _is_word_boundary(self, text, start, end):
        """Check if match is at word boundaries"""
        if start > 0 and text[start-1].isalnum():
            return False
        if end < len(text) and text[end].isalnum():
            return False
        return True
    
    def _fuzzy_match(self, text, firm_name):
        """Perform fuzzy matching for firm names"""
        matches = []
        words = text.split()
        firm_words = firm_name.lower().split()
        
        # Look for fuzzy matches of the firm name
        for i in range(len(words) - len(firm_words) + 1):
            candidate = ' '.join(words[i:i+len(firm_words)])
            ratio = fuzz.ratio(candidate, firm_name.lower())
            
            if ratio >= 80:  # Threshold for fuzzy matching
                start = text.find(candidate)
                if start != -1:
                    matches.append((firm_name, candidate, start, start + len(candidate)))
        
        return matches

class ProgramClassifier:
    def classify(self, text):
        """Classify program type based on text content"""
        text_lower = text.lower()
        
        # Check for explicit program mentions
        if any(word in text_lower for word in ['clerkship', 'clerk']):
            # Check for seasonal/timing specifics
            if any(word in text_lower for word in ['summer', 'seasonal', 'nov', 'dec', 'jan', 'feb']):
                return 'summer_clerkship'
            elif any(word in text_lower for word in ['winter', 'jun', 'jul', 'aug']):
                return 'winter_clerkship'
            elif 'vacation' in text_lower:
                return 'vacation'
            else:
                return 'clerkship'
        
        if any(phrase in text_lower for phrase in ['graduate program', 'grad program', 'graduate role', 'graduate intake']):
            return 'graduate'
        
        if any(phrase in text_lower for phrase in ['vacation program', 'vacationer']):
            return 'vacation'
        
        if 'internship' in text_lower:
            return 'internship'
        
        # Check for ambiguous program signals
        program_signals = ['program', 'intake', 'application', 'recruitment', 'hiring']
        if any(signal in text_lower for signal in program_signals):
            return 'ambiguous'
        
        return 'no_program'

class DateParser:
    def __init__(self):
        self.tz_aest = pytz.timezone('Australia/Sydney')
        
    def extract_application_dates(self, text):
        """Extract application open and close dates"""
        open_date = None
        close_date = None
        
        # Patterns for date extraction
        open_patterns = [
            r'application[s]?\s+open[s]?\s+(?:on|from)?\s*([^.!?]+)',
            r'open[s]?\s+(?:on|from)?\s*([^.!?]+)',
        ]
        
        close_patterns = [
            r'application[s]?\s+close[s]?\s+(?:on|by|at)?\s*([^.!?]+)',
            r'close[s]?\s+(?:on|by|at)?\s*([^.!?]+)',
            r'deadline[s]?\s+(?:is|on|by)?\s*([^.!?]+)'
        ]
        
        text_lower = text.lower()
        
        for pattern in open_patterns:
            match = re.search(pattern, text_lower)
            if match:
                date_str = match.group(1).strip()
                parsed_date = self._parse_date_string(date_str)
                if parsed_date:
                    open_date = parsed_date
                    break
        
        for pattern in close_patterns:
            match = re.search(pattern, text_lower)
            if match:
                date_str = match.group(1).strip()
                parsed_date = self._parse_date_string(date_str)
                if parsed_date:
                    close_date = parsed_date
                    break
        
        return open_date, close_date
    
    def _parse_date_string(self, date_str):
        """Parse various date string formats"""
        try:
            # Clean up the date string
            date_str = re.sub(r'[^\w\s\-/]', '', date_str)
            
            # Try parsing with dateutil
            parsed = date_parser.parse(date_str, fuzzy=True)
            return parsed.strftime('%Y-%m-%d')
        except:
            # Try manual parsing for common formats
            month_patterns = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            for month_name, month_num in month_patterns.items():
                if month_name in date_str.lower():
                    # Extract year if present
                    year_match = re.search(r'20\d{2}', date_str)
                    year = year_match.group(0) if year_match else '2025'
                    
                    # Extract day if present
                    day_match = re.search(r'\b(\d{1,2})\b', date_str)
                    day = day_match.group(1).zfill(2) if day_match else '01'
                    
                    return f"{year}-{month_num}-{day}"
            
            return None
    
    def parse_timestamp(self, timestamp_str):
        """Parse timestamp to UTC"""
        if not timestamp_str:
            return timestamp_str
        
        try:
            # Handle AEST/AEDT timestamps
            if 'aest' in timestamp_str.lower() or 'aedt' in timestamp_str.lower():
                clean_ts = re.sub(r'\s+aest|\s+aedt', '', timestamp_str.lower())
                parsed = date_parser.parse(clean_ts, fuzzy=True)
                
                # Assume AEST timezone
                localized = self.tz_aest.localize(parsed)
                utc_time = localized.astimezone(pytz.UTC)
                return utc_time.isoformat()
            else:
                parsed = date_parser.parse(timestamp_str, fuzzy=True)
                return parsed.isoformat()
        except:
            return timestamp_str

class ConfidenceCalculator:
    def calculate(self, firm_alias, firm_name, program_type, city, intake_year, 
                  open_date, close_date, num_firms_in_span):
        """Calculate confidence score 0-1"""
        confidence = 0.5  # Base confidence
        
        # Firm match quality
        if firm_alias.lower() in [alias.lower() for alias in FIRM_ALIASES.get(firm_name, [])]:
            confidence += 0.2  # Exact alias match
        else:
            confidence += 0.1  # Fuzzy match
        
        # Program type explicitness
        if program_type in ['clerkship', 'graduate', 'summer_clerkship', 'winter_clerkship']:
            confidence += 0.1
        
        # Additional signals
        if city and city != 'Other/Unknown':
            confidence += 0.05
        
        if intake_year:
            confidence += 0.05
        
        if open_date or close_date:
            confidence += 0.05
        
        # Penalties
        if close_date and not open_date:
            confidence -= 0.1  # Month-only date
        
        if num_firms_in_span > 1:
            confidence -= 0.1  # Multiple firms in same span
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, confidence))

class EvidenceExtractor:
    def extract_evidence(self, context, firm_alias, program_type):
        """Extract evidence span around firm and program keywords"""
        # Find the firm mention
        firm_idx = context.lower().find(firm_alias.lower())
        if firm_idx == -1:
            return context[:240]
        
        # Find program keywords
        program_keywords = ['clerkship', 'graduate', 'program', 'application', 'intern']
        keyword_indices = []
        
        for keyword in program_keywords:
            idx = context.lower().find(keyword)
            if idx != -1:
                keyword_indices.append(idx)
        
        if not keyword_indices:
            # No program keywords, just return context around firm
            start = max(0, firm_idx - 100)
            end = min(len(context), firm_idx + 140)
            return context[start:end].strip()
        
        # Find the span that includes firm and closest program keyword
        min_idx = min([firm_idx] + keyword_indices)
        max_idx = max([firm_idx] + keyword_indices)
        
        # Expand to get full context
        start = max(0, min_idx - 50)
        end = min(len(context), max_idx + 50)
        
        evidence = context[start:end].strip()
        
        # Truncate to 240 chars if needed
        if len(evidence) > 240:
            evidence = evidence[:237] + "..."
        
        return evidence
