import re
import json
import logging
from typing import List, Dict, Any

class KPIExtractor:
    def __init__(self):
        """Initialize KPI extractor with financial metric patterns"""
        self.financial_patterns = {
            'revenue': [
                r'revenue\s*(?:of\s*)?[\$]?([\d,\.]+)\s*(?:million|billion|k|m|b)?',
                r'sales\s*(?:of\s*)?[\$]?([\d,\.]+)\s*(?:million|billion|k|m|b)?',
                r'total\s*revenue\s*[\$]?([\d,\.]+)\s*(?:million|billion|k|m|b)?'
            ],
            'profit': [
                r'profit\s*(?:of\s*)?[\$]?([\d,\.]+)\s*(?:million|billion|k|m|b)?',
                r'net\s*income\s*[\$]?([\d,\.]+)\s*(?:million|billion|k|m|b)?',
                r'earnings\s*[\$]?([\d,\.]+)\s*(?:million|billion|k|m|b)?'
            ],
            'margin': [
                r'(?:profit\s*)?margin\s*(?:of\s*)?([\d,\.]+)%?',
                r'(?:gross\s*)?margin\s*[\:]?\s*([\d,\.]+)%',
                r'operating\s*margin\s*[\:]?\s*([\d,\.]+)%'
            ],
            'eps': [
                r'earnings\s*per\s*share\s*[\$]?([\d,\.]+)',
                r'eps\s*[\$]?([\d,\.]+)',
                r'diluted\s*eps\s*[\$]?([\d,\.]+)'
            ],
            'market_cap': [
                r'market\s*cap(?:italization)?\s*[\$]?([\d,\.]+)\s*(?:million|billion|k|m|b)?',
                r'market\s*value\s*[\$]?([\d,\.]+)\s*(?:million|billion|k|m|b)?'
            ],
            'pe_ratio': [
                r'p\/e\s*ratio\s*([\d,\.]+)',
                r'price\s*to\s*earnings\s*([\d,\.]+)',
                r'pe\s*ratio\s*([\d,\.]+)'
            ]
        }
        
        self.company_patterns = [
            r'\b([A-Z]{2,5})\b',  # Stock symbols
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc|Corp|Company|Ltd)\b',  # Company names
            r'\b(Apple|Microsoft|Google|Amazon|Tesla|Meta|Netflix|Nvidia)\b'  # Common companies
        ]
    
    def extract_kpis(self, text: str) -> Dict[str, Any]:
        """Extract KPIs and financial metrics from text"""
        try:
            extracted_kpis = {
                'metrics': {},
                'companies': [],
                'time_periods': [],
                'currencies': [],
                'confidence_score': 0.0
            }
            
            text_lower = text.lower()
            
            # Extract financial metrics
            for metric_type, patterns in self.financial_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                    for match in matches:
                        value = self._normalize_value(match.group(1))
                        if value is not None:
                            if metric_type not in extracted_kpis['metrics']:
                                extracted_kpis['metrics'][metric_type] = []
                            extracted_kpis['metrics'][metric_type].append({
                                'value': value,
                                'raw_text': match.group(0),
                                'position': match.span()
                            })
            
            # Extract companies
            extracted_kpis['companies'] = self._extract_companies(text)
            
            # Extract time periods
            extracted_kpis['time_periods'] = self._extract_time_periods(text)
            
            # Extract currencies
            extracted_kpis['currencies'] = self._extract_currencies(text)
            
            # Calculate confidence score
            extracted_kpis['confidence_score'] = self._calculate_confidence(extracted_kpis)
            
            logging.info(f"Extracted KPIs: {extracted_kpis}")
            return extracted_kpis
            
        except Exception as e:
            logging.error(f"Error extracting KPIs: {str(e)}")
            return {
                'metrics': {},
                'companies': [],
                'time_periods': [],
                'currencies': [],
                'confidence_score': 0.0,
                'error': str(e)
            }
    
    def _normalize_value(self, value_str: str) -> float:
        """Normalize extracted numerical values"""
        try:
            # Remove commas and convert to float
            clean_value = re.sub(r'[,\s]', '', value_str)
            return float(clean_value)
        except (ValueError, TypeError):
            return 0.0
    
    def _extract_companies(self, text: str) -> List[Dict[str, Any]]:
        """Extract company names and stock symbols"""
        companies = []
        for pattern in self.company_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                companies.append({
                    'name': match.group(1),
                    'type': 'symbol' if match.group(1).isupper() and len(match.group(1)) <= 5 else 'name',
                    'position': match.span()
                })
        return companies
    
    def _extract_time_periods(self, text: str) -> List[Dict[str, Any]]:
        """Extract time periods (quarters, years, etc.)"""
        time_patterns = [
            r'(\d{4})',  # Years
            r'(Q[1-4]\s*\d{4})',  # Quarters
            r'(FY\s*\d{4})',  # Fiscal years
            r'(\d{1,2}\/\d{1,2}\/\d{2,4})',  # Dates
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s*\d{4}',  # Month Year
        ]
        
        time_periods = []
        for pattern in time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                time_periods.append({
                    'period': match.group(1),
                    'position': match.span()
                })
        return time_periods
    
    def _extract_currencies(self, text: str) -> List[str]:
        """Extract currency indicators"""
        currency_patterns = [
            r'\$',  # Dollar sign
            r'USD',
            r'EUR',
            r'GBP',
            r'JPY',
            r'dollars?',
            r'euros?',
            r'pounds?'
        ]
        
        currencies = []
        for pattern in currency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                currencies.append(pattern.replace('?', '').replace('\\', ''))
        
        return list(set(currencies))  # Remove duplicates
    
    def _calculate_confidence(self, extracted_kpis: Dict[str, Any]) -> float:
        """Calculate confidence score based on extracted information"""
        score = 0.0
        
        # Points for extracted metrics
        if extracted_kpis['metrics']:
            score += min(len(extracted_kpis['metrics']) * 0.2, 0.6)
        
        # Points for company identification
        if extracted_kpis['companies']:
            score += 0.2
        
        # Points for time periods
        if extracted_kpis['time_periods']:
            score += 0.1
        
        # Points for currency identification
        if extracted_kpis['currencies']:
            score += 0.1
        
        return min(score, 1.0)
