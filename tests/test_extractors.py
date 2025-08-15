
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors import FirmMatcher, DateParser, ProgramClassifier, ConfidenceCalculator

def test_firm_matching():
    matcher = FirmMatcher()
    
    # Test exact alias match
    text = "I got an offer from Clutz for their summer clerkship"
    matches = matcher.find_firms(text)
    assert len(matches) > 0
    assert matches[0][0] == "Clayton Utz"
    assert matches[0][1] == "clutz"
    
    # Test full name match
    text = "Herbert Smith Freehills sent out interviews"
    matches = matcher.find_firms(text)
    assert len(matches) > 0
    assert matches[0][0] == "Herbert Smith Freehills"

def test_date_parsing():
    parser = DateParser()
    
    # Test various date formats
    assert parser._parse_date_string("15 Aug 2025") == "2025-08-15"
    assert parser._parse_date_string("Aug 15, 2025") == "2025-08-15"
    assert parser._parse_date_string("2025-Aug-15") is not None
    
    # Test application date extraction
    text = "Applications close on 15 August 2025"
    open_date, close_date = parser.extract_application_dates(text)
    assert close_date == "2025-08-15"

def test_program_classification():
    classifier = ProgramClassifier()
    
    assert classifier.classify("summer clerkship at Allens") == "summer_clerkship"
    assert classifier.classify("graduate program applications") == "graduate"
    assert classifier.classify("vacation program at KWM") == "vacation"
    assert classifier.classify("general discussion about law") == "no_program"

def test_salary_extraction():
    from extract_grad_programs import extract_salary
    
    assert extract_salary("salary is $65k") == 65000
    assert extract_salary("starting at $85,000") == 85000
    assert extract_salary("$70k+super package") == 70000

def test_confidence_calculation():
    calc = ConfidenceCalculator()
    
    # High confidence case
    confidence = calc.calculate("allens", "Allens", "clerkship", "Sydney", 2025, 
                               "2025-08-01", "2025-08-15", 1)
    assert confidence > 0.7
    
    # Low confidence case
    confidence = calc.calculate("unknown", "Unknown Firm", "ambiguous", None, None, 
                               None, None, 3)
    assert confidence < 0.6

if __name__ == "__main__":
    pytest.main([__file__])
