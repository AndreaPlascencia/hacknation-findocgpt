# Financial Chatbot - FinanceBench AI Assistant

## Overview

This is a comprehensive financial chatbot application built with Flask and Socket.IO that provides intelligent financial analysis, KPI extraction, forecasting, and real-time chat capabilities. The system integrates with FinanceBench for financial data retrieval and uses OpenAI for natural language processing and embeddings. The application serves as an AI-powered assistant for financial queries, capable of extracting key performance indicators, generating forecasts, and providing contextual responses using a RAG (Retrieval-Augmented Generation) system.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
The application follows a modular Flask architecture with specialized components:

- **Flask Web Server**: Serves the main application with Socket.IO for real-time communication
- **SQLAlchemy ORM**: Handles database operations with support for SQLite (default) or PostgreSQL via DATABASE_URL environment variable
- **Component-Based Design**: Separate modules for distinct functionalities (KPI extraction, RAG system, forecasting, FinanceBench integration)

### Core Components

**ChatBot Engine**: Central orchestrator that coordinates between different specialized systems to process user messages and generate comprehensive responses including KPI extraction, contextual information retrieval, and forecasting.

**KPI Extractor**: Uses regex patterns to identify and extract financial metrics from natural language, including revenue, profit, margins, EPS, market cap, and P/E ratios, along with company identification.

**RAG System**: Implements retrieval-augmented generation using OpenAI embeddings (text-embedding-ada-002) with cosine similarity search for contextual document retrieval and chunked document processing.

**Financial Forecaster**: Provides forecasting capabilities using machine learning models (Linear Regression and Random Forest) with configurable forecast periods and confidence intervals.

**FinanceBench Client**: Handles external financial data integration with caching mechanisms and query parsing for financial metrics retrieval.

### Data Architecture

**Database Models**:
- ChatSession and ChatMessage: Store conversation history
- FinancialData: Cache financial metrics with company, period, and source tracking
- VectorEmbedding: Store document embeddings for RAG system with content type classification

**Data Flow**: User queries flow through intent analysis, KPI extraction, RAG context retrieval, and response generation with optional financial data and forecasting integration.

### Frontend Architecture

**Real-time Interface**: Bootstrap-based dark theme UI with Socket.IO for instant messaging, featuring quick action buttons for common financial queries and chart visualization capabilities using Chart.js.

**Responsive Design**: Mobile-friendly layout with sidebar navigation, typing indicators, and modal-based chart displays.

## External Dependencies

### Core Services
- **OpenAI API**: Natural language processing, embeddings generation, and response generation
- **FinanceBench API**: Financial data provider (configurable via environment variables)

### Python Libraries
- **Flask & Flask-SocketIO**: Web framework and real-time communication
- **SQLAlchemy**: Database ORM with PostgreSQL/SQLite support
- **OpenAI Python Client**: API integration for AI services
- **Scikit-learn**: Machine learning models for forecasting (Linear Regression, Random Forest)
- **NumPy & Pandas**: Data processing and numerical operations

### Frontend Dependencies
- **Bootstrap 5**: UI framework with dark theme support
- **Font Awesome**: Icon library
- **Chart.js**: Data visualization
- **Socket.IO Client**: Real-time communication

### Environment Configuration
- `OPENAI_API_KEY`: Required for AI functionality
- `DATABASE_URL`: Database connection (defaults to SQLite)
- `SESSION_SECRET`: Flask session security
- `FINANCEBENCH_API_URL` & `FINANCEBENCH_API_KEY`: External financial data service