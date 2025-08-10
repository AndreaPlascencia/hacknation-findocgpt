import os
import logging
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from werkzeug.middleware.proxy_fix import ProxyFix

from db_core import db


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
#socketio = SocketIO(app, cors_allowed_origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet", ping_interval=25, ping_timeout=60)


# Set up logging
#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("findocgpt")
logger.setLevel(logging.INFO)


with app.app_context():
    import models
    db.create_all()

from chatbot import ChatBot

# Initialize chatbot
chatbot = ChatBot()

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logging.info('Client connected')
    emit('status', {'msg': 'Connected to Financial Chatbot'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logging.info('Client disconnected')

@socketio.on('message')
def handle_message(data):
    """Handle incoming chat messages"""
    try:
        logging.info("Tryng to handle message")
        user_message = data.get('message', '')
        logging.info(f'Received message: {user_message}')
        
        # Emit typing indicator
        emit('typing', {'typing': True})
        
        # Process message through chatbot
        response = chatbot.process_message(user_message)
        
        # Stop typing indicator and send response
        emit('typing', {'typing': False})
        emit('response', response)
        
    except Exception as e:
        logging.error(f'Error processing message: {str(e)}')
        emit('typing', {'typing': False})
        emit('error', {'message': f'Error processing your request: {str(e)}'})

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f'Internal error: {str(error)}')
    return render_template('index.html'), 500
