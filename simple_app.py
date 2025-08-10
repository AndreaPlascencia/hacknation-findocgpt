import os
import json
import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

# Import the shared database instance
from app import db

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///chatbot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)

# Set up logging
logging.basicConfig(level=logging.INFO)

with app.app_context():
    import models
    db.create_all()

from chatbot import ChatBot

# Initialize chatbot
chatbot = ChatBot()

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index_en.html')

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """Handle chat API requests"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        logging.info(f'Received message: {user_message}')
        
        # Process message through chatbot
        response = chatbot.process_message(user_message)
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f'Error processing message: {str(e)}')
        return jsonify({
            'error': True,
            'message': f'Error processing your request: {str(e)}'
        }), 500

@app.route('/api/status')
def status():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Financial Chatbot is running'})

@app.errorhandler(404)
def not_found(error):
    return render_template('simple_index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f'Internal error: {str(error)}')
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Initialize RAG system
    try:
        from rag_system import RAGSystem
        rag = RAGSystem()
        logging.info("RAG system initialized")
    except Exception as e:
        logging.error(f"Error initializing RAG system: {str(e)}")
    
    app.run(host='0.0.0.0', port=5000, debug=False)