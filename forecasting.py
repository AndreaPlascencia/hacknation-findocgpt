import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

class FinancialForecaster:
    def __init__(self):
        """Initialize financial forecasting system"""
        self.models = {
            'linear_regression': LinearRegression(),
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42)
        }
        self.default_periods = 4  # Default forecast periods (quarters)
        
    def generate_forecast(self, query: str, kpis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate financial forecast based on query and extracted KPIs"""
        try:
            # Extract forecast parameters from query
            forecast_params = self._parse_forecast_request(query, kpis)
            
            # Generate sample historical data (in production, this would come from FinanceBench)
            historical_data = self._get_historical_data(forecast_params)
            
            # Generate forecast
            forecast_result = self._create_forecast(historical_data, forecast_params)
            
            return {
                'forecast_data': forecast_result,
                'parameters': forecast_params,
                'historical_periods': len(historical_data),
                'forecast_periods': forecast_params.get('periods', self.default_periods),
                'confidence_interval': self._calculate_confidence_interval(forecast_result),
                'methodology': 'Time series analysis with linear regression',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error generating forecast: {str(e)}")
            return {
                'error': str(e),
                'message': 'Unable to generate forecast with available data'
            }
    
    def _parse_forecast_request(self, query: str, kpis: Dict[str, Any]) -> Dict[str, Any]:
        """Parse forecast request to extract parameters"""
        params = {
            'metric': 'revenue',  # Default metric
            'periods': self.default_periods,
            'company': None,
            'method': 'linear_regression'
        }
        
        query_lower = query.lower()
        
        # Determine forecast metric
        if 'profit' in query_lower or 'earnings' in query_lower:
            params['metric'] = 'profit'
        elif 'revenue' in query_lower or 'sales' in query_lower:
            params['metric'] = 'revenue'
        elif 'margin' in query_lower:
            params['metric'] = 'margin'
        elif 'eps' in query_lower:
            params['metric'] = 'eps'
        
        # Extract number of periods
        import re
        period_match = re.search(r'(\d+)\s*(?:quarters?|periods?|months?)', query_lower)
        if period_match:
            params['periods'] = int(period_match.group(1))
        
        # Extract company from KPIs
        if kpis.get('companies'):
            params['company'] = kpis['companies'][0]['name']
        
        return params
    
    def _get_historical_data(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get historical data for forecasting (simulated data for demo)"""
        # In production, this would query FinanceBench or database
        # For now, generate realistic sample data
        
        metric = params['metric']
        periods = 12  # Historical periods to use for forecasting
        
        # Generate base trend with seasonality and noise
        np.random.seed(42)  # For reproducible results
        
        base_values = {
            'revenue': 1000,  # Million USD
            'profit': 150,
            'margin': 15.0,   # Percentage
            'eps': 2.50       # USD
        }
        
        base_value = base_values.get(metric, 1000)
        trend = 0.05  # 5% growth trend
        seasonality = 0.1  # 10% seasonal variation
        noise = 0.05  # 5% random noise
        
        historical_data = []
        for i in range(periods):
            # Calculate date (quarterly data going back)
            date = datetime.utcnow() - timedelta(days=90 * (periods - i - 1))
            
            # Calculate value with trend, seasonality, and noise
            trend_value = base_value * (1 + trend) ** i
            seasonal_factor = 1 + seasonality * np.sin(2 * np.pi * i / 4)  # Quarterly seasonality
            noise_factor = 1 + noise * np.random.normal(0, 1)
            
            value = trend_value * seasonal_factor * noise_factor
            
            historical_data.append({
                'date': date.strftime('%Y-Q%d') if i % 3 == 2 else date.strftime('%Y-%m'),
                'period': i + 1,
                'value': round(value, 2),
                'metric': metric
            })
        
        return historical_data
    
    def _create_forecast(self, historical_data: List[Dict], params: Dict[str, Any]) -> Dict[str, Any]:
        """Create forecast using machine learning models"""
        try:
            # Prepare data for modeling
            df = pd.DataFrame(historical_data)
            X = df[['period']].values
            y = df['value'].values
            
            # Train models
            forecasts = {}
            
            for model_name, model in self.models.items():
                model.fit(X, y)
                
                # Generate forecast
                forecast_periods = range(
                    len(historical_data) + 1,
                    len(historical_data) + 1 + params['periods']
                )
                
                X_forecast = np.array(forecast_periods).reshape(-1, 1)
                y_forecast = model.predict(X_forecast)
                
                # Calculate model performance on historical data
                y_pred_hist = model.predict(X)
                mae = mean_absolute_error(y, y_pred_hist)
                rmse = np.sqrt(mean_squared_error(y, y_pred_hist))
                
                forecasts[model_name] = {
                    'values': [round(val, 2) for val in y_forecast],
                    'periods': list(forecast_periods),
                    'mae': round(mae, 2),
                    'rmse': round(rmse, 2)
                }
            
            # Use the best performing model (lowest RMSE)
            best_model = min(forecasts.keys(), key=lambda k: forecasts[k]['rmse'])
            
            # Generate forecast dates
            forecast_dates = []
            for i in range(params['periods']):
                future_date = datetime.utcnow() + timedelta(days=90 * (i + 1))
                forecast_dates.append(future_date.strftime('%Y-Q%d'))
            
            return {
                'method_used': best_model,
                'forecast_values': forecasts[best_model]['values'],
                'forecast_dates': forecast_dates,
                'model_performance': {
                    'mae': forecasts[best_model]['mae'],
                    'rmse': forecasts[best_model]['rmse']
                },
                'historical_values': [round(val, 2) for val in y],
                'historical_dates': [item['date'] for item in historical_data]
            }
            
        except Exception as e:
            logging.error(f"Error in _create_forecast: {str(e)}")
            raise e
    
    def _calculate_confidence_interval(self, forecast_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate confidence intervals for forecast"""
        try:
            if 'forecast_values' not in forecast_result:
                return {}
            
            # Simple confidence interval based on historical variance
            forecast_values = forecast_result['forecast_values']
            historical_values = forecast_result.get('historical_values', [])
            
            if not historical_values:
                return {}
            
            # Calculate standard deviation of historical data
            hist_std = np.std(historical_values)
            
            # 95% confidence interval (±1.96 standard deviations)
            confidence_95 = []
            for value in forecast_values:
                lower_bound = round(value - 1.96 * hist_std, 2)
                upper_bound = round(value + 1.96 * hist_std, 2)
                confidence_95.append({
                    'forecast': value,
                    'lower_95': lower_bound,
                    'upper_95': upper_bound
                })
            
            return {
                'confidence_95': confidence_95,
                'standard_deviation': round(hist_std, 2)
            }
            
        except Exception as e:
            logging.error(f"Error calculating confidence interval: {str(e)}")
            return {}
