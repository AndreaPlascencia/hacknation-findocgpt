import os
import json
import logging
from datetime import datetime
from openai import OpenAI
from kpi_extractor import KPIExtractor
from rag_system import RAGSystem
from forecasting import FinancialForecaster
from financebench_client import FinanceBenchClient

class ChatBot:
    def __init__(self):
        """Initialize the financial chatbot"""
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.kpi_extractor = KPIExtractor()
        self.rag_system = RAGSystem()
        self.forecaster = FinancialForecaster()
        self.financebench_client = FinanceBenchClient()
        
    def process_message(self, user_message):
        """Process user message and generate comprehensive response"""
        try:
            # Analyze user intent
            intent = self._analyze_intent(user_message)
            
            # Extract KPIs from the message
            extracted_kpis = self.kpi_extractor.extract_kpis(user_message)
            
            # Get relevant context using RAG
            rag_context = self.rag_system.get_relevant_context(user_message)

            # Bandera para el cliente / logs
            if rag_context:
                rag_used = bool(rag_context and rag_context.strip())
                logging.info(f"RAG used={rag_used} query='{user_message[:80]}'")
            else:
                logging.info(f"RAG not used")
            
            # Generate main response
            main_response = self._generate_response(user_message, intent, rag_context)
            
            # Add financial data if requested
            financial_data = None
            if intent.get('needs_financial_data', False):
                financial_data = self._get_financial_data(user_message, extracted_kpis)
            
            # Add forecasting if requested
            forecast_data = None
            if intent.get('needs_forecasting', False):
                forecast_data = self._generate_forecast(user_message, extracted_kpis)
            
            # Compile response
            response = {
                'message': main_response,
                'kpis': extracted_kpis,
                'financial_data': financial_data,
                'forecast': forecast_data,
                'timestamp': datetime.utcnow().isoformat(),
                'has_charts': bool(financial_data or forecast_data)
            }
            
            return response
            
        except Exception as e:
            logging.error(f"Error in process_message: {str(e)}")
            return {
                'message': f"I apologize, but I encountered an error while processing your request: {str(e)}",
                'error': True,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _analyze_intent(self, message):
        """Analyze user intent to determine response strategy"""
        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a financial intent analyzer. Analyze the user's message and determine:
                        1. Whether they need financial data from FinanceBench
                        2. Whether they need forecasting/prediction
                        3. The main topic or company they're asking about
                        4. The type of financial information requested
                        
                        Respond with JSON in this format:
                        {
                            "needs_financial_data": boolean,
                            "needs_forecasting": boolean,
                            "company": "string or null",
                            "topic": "string",
                            "query_type": "kpi|comparison|analysis|forecast|general"
                        }"""
                    },
                    {"role": "user", "content": message}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
            else:
                raise ValueError("Empty response from OpenAI")
            
        except Exception as e:
            logging.error(f"Error analyzing intent: {str(e)}")
            return {
                "needs_financial_data": False,
                "needs_forecasting": False,
                "company": None,
                "topic": "general",
                "query_type": "general"
            }
    
    def _generate_response(self, user_message, intent, rag_context):
        """Generate main chatbot response"""
        try:
            system_prompt = """You are a helpful financial assistant with access to FinanceBench data, 
            KPI extraction capabilities, and forecasting tools. Provide clear, accurate, and helpful responses 
            to financial queries. Use the provided context to enhance your responses, but clearly indicate 
            when information comes from external sources."""
            
            context_info = ""
            if rag_context:
                context_info = f"\n\nRelevant context:\n{rag_context}"
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{user_message}{context_info}"}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again."
    
    def _get_financial_data(self, message, kpis):
        """Get financial data based on user query and extracted KPIs"""
        try:
            return self.financebench_client.query_financial_data(message, kpis)
        except Exception as e:
            logging.error(f"Error getting financial data: {str(e)}")
            return None
    
    def _generate_forecast(self, message, kpis):
        """Generate financial forecast based on user query"""
        try:
            return self.forecaster.generate_forecast(message, kpis)
        except Exception as e:
            logging.error(f"Error generating forecast: {str(e)}")
            return None
