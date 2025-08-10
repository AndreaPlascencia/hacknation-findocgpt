import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from models import FinancialData
from db_core import db

class FinanceBenchClient:
    def __init__(self):
        """Initialize FinanceBench client"""
        # In a real implementation, this would connect to actual FinanceBench API
        self.api_base_url = os.getenv("FINANCEBENCH_API_URL", "https://api.financebench.com/v1")
        self.api_key = os.getenv("FINANCEBENCH_API_KEY", "demo-key")
        
    def query_financial_data(self, query: str, kpis: Dict[str, Any]) -> Dict[str, Any]:
        """Query financial data based on user request and extracted KPIs"""
        try:
            # Parse query to determine what data to retrieve
            query_params = self._parse_query(query, kpis)
            
            # Get data from cache or external source
            financial_data = self._get_cached_or_fetch_data(query_params)
            
            # Format data for response
            formatted_data = self._format_financial_data(financial_data, query_params)
            
            return {
                'data': formatted_data,
                'query_parameters': query_params,
                'data_source': 'FinanceBench',
                'timestamp': datetime.utcnow().isoformat(),
                'total_records': len(financial_data)
            }
            
        except Exception as e:
            logging.error(f"Error querying financial data: {str(e)}")
            return {
                'error': str(e),
                'message': 'Unable to retrieve financial data'
            }
    
    def _parse_query(self, query: str, kpis: Dict[str, Any]) -> Dict[str, Any]:
        """Parse query to extract search parameters"""
        params = {
            'companies': [],
            'metrics': [],
            'time_periods': [],
            'data_type': 'quarterly'
        }
        
        # Extract companies from KPIs
        if kpis.get('companies'):
            params['companies'] = [comp['name'] for comp in kpis['companies']]
        
        # Extract metrics from KPIs
        if kpis.get('metrics'):
            params['metrics'] = list(kpis['metrics'].keys())
        
        # Extract time periods
        if kpis.get('time_periods'):
            params['time_periods'] = [period['period'] for period in kpis['time_periods']]
        
        # Default to major companies if none specified
        if not params['companies']:
            params['companies'] = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'][:3]  # Top 3 for demo
        
        # Default to revenue if no metrics specified
        if not params['metrics']:
            params['metrics'] = ['revenue', 'profit', 'margin']
        
        return params
    
    def _get_cached_or_fetch_data(self, params: Dict[str, Any]) -> List[FinancialData]:
        """Get data from cache or fetch from external source"""
        try:
            # Check cache first
            cached_data = self._get_from_cache(params)
            if cached_data:
                return cached_data
            
            # Fetch from external source (simulated for demo)
            fresh_data = self._fetch_external_data(params)
            
            # Cache the data
            self._cache_data(fresh_data)
            
            return fresh_data
            
        except Exception as e:
            logging.error(f"Error getting financial data: {str(e)}")
            return []
    
    def _get_from_cache(self, params: Dict[str, Any]) -> List[FinancialData]:
        """Get data from database cache"""
        try:
            query = FinancialData.query
            
            if params['companies']:
                query = query.filter(FinancialData.company_symbol.in_(params['companies']))
            
            if params['metrics']:
                query = query.filter(FinancialData.metric_name.in_(params['metrics']))
            
            # Only return recent data (less than 24 hours old)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            query = query.filter(FinancialData.updated_at > recent_cutoff)
            
            return query.all()
            
        except Exception as e:
            logging.error(f"Error getting cached data: {str(e)}")
            return []
    
    def _fetch_external_data(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch data from external FinanceBench API (simulated)"""
        # In production, this would make actual API calls to FinanceBench
        # For demo purposes, generate realistic sample data
        
        sample_data = []
        import numpy as np
        np.random.seed(42)
        
        for company in params['companies']:
            for metric in params['metrics']:
                # Generate sample quarterly data for the last 8 quarters
                for quarter in range(1, 9):
                    year = 2023 if quarter <= 4 else 2024
                    q = quarter if quarter <= 4 else quarter - 4
                    
                    # Generate realistic values based on metric type
                    base_values = {
                        'revenue': np.random.normal(25000, 5000),  # Million USD
                        'profit': np.random.normal(5000, 1000),
                        'margin': np.random.normal(20, 5),  # Percentage
                        'eps': np.random.normal(3.5, 0.5),
                        'market_cap': np.random.normal(500000, 100000),
                        'pe_ratio': np.random.normal(25, 5)
                    }
                    
                    value = max(0, base_values.get(metric, 1000))
                    
                    sample_data.append({
                        'company_symbol': company,
                        'metric_name': metric,
                        'metric_value': round(value, 2),
                        'period': f"Q{q}",
                        'year': year,
                        'quarter': q,
                        'data_source': 'FinanceBench_Demo'
                    })
        
        return sample_data
    
    def _cache_data(self, data_list: List[Dict[str, Any]]):
        """Cache data in database"""
        try:
            for data_item in data_list:
                financial_data = FinancialData(
                    company_symbol=data_item['company_symbol'],
                    metric_name=data_item['metric_name'],
                    metric_value=data_item['metric_value'],
                    period=data_item['period'],
                    year=data_item['year'],
                    quarter=data_item.get('quarter'),
                    data_source=data_item['data_source']
                )
                db.session.add(financial_data)
            
            db.session.commit()
            logging.info(f"Cached {len(data_list)} financial data records")
            
        except Exception as e:
            logging.error(f"Error caching data: {str(e)}")
            db.session.rollback()
    
    def _format_financial_data(self, data: List, params: Dict[str, Any]) -> Dict[str, Any]:
        """Format financial data for response"""
        try:
            formatted = {
                'companies': {},
                'metrics': {},
                'time_series': {},
                'summary': {}
            }
            
            # Convert SQLAlchemy objects to dict if needed
            data_dicts = []
            for item in data:
                if hasattr(item, '__dict__'):
                    data_dict = {
                        'company_symbol': item.company_symbol,
                        'metric_name': item.metric_name,
                        'metric_value': item.metric_value,
                        'period': item.period,
                        'year': item.year,
                        'quarter': item.quarter
                    }
                else:
                    data_dict = item
                data_dicts.append(data_dict)
            
            # Group by company
            for item in data_dicts:
                company = item['company_symbol']
                if company not in formatted['companies']:
                    formatted['companies'][company] = []
                formatted['companies'][company].append(item)
            
            # Group by metric
            for item in data_dicts:
                metric = item['metric_name']
                if metric not in formatted['metrics']:
                    formatted['metrics'][metric] = []
                formatted['metrics'][metric].append(item)
            
            # Create time series data for charting
            for item in data_dicts:
                key = f"{item['company_symbol']}_{item['metric_name']}"
                if key not in formatted['time_series']:
                    formatted['time_series'][key] = {
                        'company': item['company_symbol'],
                        'metric': item['metric_name'],
                        'data_points': []
                    }
                
                formatted['time_series'][key]['data_points'].append({
                    'period': f"{item['year']}-{item['period']}",
                    'value': item['metric_value'],
                    'year': item['year'],
                    'quarter': item.get('quarter')
                })
            
            # Sort time series data by period
            for key in formatted['time_series']:
                formatted['time_series'][key]['data_points'].sort(
                    key=lambda x: (x['year'], x.get('quarter', 0))
                )
            
            # Generate summary statistics
            formatted['summary'] = self._generate_summary_stats(data_dicts)
            
            return formatted
            
        except Exception as e:
            logging.error(f"Error formatting financial data: {str(e)}")
            return {'error': str(e)}
    
    def _generate_summary_stats(self, data: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics from financial data"""
        try:
            summary = {
                'total_records': len(data),
                'companies_count': len(set(item['company_symbol'] for item in data)),
                'metrics_count': len(set(item['metric_name'] for item in data)),
                'date_range': {
                    'earliest': min(item['year'] for item in data) if data else None,
                    'latest': max(item['year'] for item in data) if data else None
                }
            }
            
            # Calculate average values by metric
            summary['metric_averages'] = {}
            for metric in set(item['metric_name'] for item in data):
                metric_values = [item['metric_value'] for item in data if item['metric_name'] == metric and item['metric_value'] is not None]
                if metric_values:
                    summary['metric_averages'][metric] = {
                        'average': round(sum(metric_values) / len(metric_values), 2),
                        'min': round(min(metric_values), 2),
                        'max': round(max(metric_values), 2),
                        'count': len(metric_values)
                    }
            
            return summary
            
        except Exception as e:
            logging.error(f"Error generating summary stats: {str(e)}")
            return {}
    
from datetime import timedelta
