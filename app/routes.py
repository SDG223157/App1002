from flask import Blueprint, render_template, request, make_response, jsonify
from datetime import datetime
import yfinance as yf
import logging
import sys
import re
import os
import traceback
from app.utils.analyzer.stock_analyzer import create_stock_visualization
from sqlalchemy import inspect, text
from flask_login import login_required, current_user

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create Blueprint
bp = Blueprint('main', __name__)

def load_tickers():
    """Load tickers from TypeScript file"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, '..', 'tickers.ts')
        
        if not os.path.exists(file_path):
            logger.error(f"Tickers file not found at: {file_path}")
            return [], {}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        pattern = r'{[^}]*symbol:\s*"([^"]*)",[^}]*name:\s*"([^"]*)"[^}]*}'
        matches = re.finditer(pattern, content)
        
        TICKERS = []
        TICKER_DICT = {}
        
        for match in matches:
            symbol, name = match.groups()
            ticker_obj = {"symbol": symbol, "name": name}
            TICKERS.append(ticker_obj)
            TICKER_DICT[symbol] = name
        
        return TICKERS, TICKER_DICT
        
    except Exception as e:
        logger.error(f"Error loading tickers: {str(e)}")
        return [], {}

# Load tickers at module level
TICKERS, TICKER_DICT = load_tickers()

@bp.route('/')
def index():
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('index.html', now=datetime.now(), max_date=today)

@bp.route('/search_ticker', methods=['GET'])
def search_ticker():
    query = request.args.get('query', '').upper()
    if not query or len(query) < 1:
        return jsonify([])
    
    try:
        search_results = []
        logger.info(f"Searching for ticker: {query}")
        
        # Exact match
        if query in TICKER_DICT:
            search_results.append({
                'symbol': query,
                'name': TICKER_DICT[query],
                'source': 'predefined'
            })
        
        # Partial matches
        if len(search_results) < 5:
            partial_matches = [
                {'symbol': ticker['symbol'], 'name': ticker['name'], 'source': 'predefined'}
                for ticker in TICKERS
                if (query in ticker['symbol'].upper() or 
                    query in ticker['name'].upper()) and 
                    ticker['symbol'] != query
            ]
            search_results.extend(partial_matches[:5 - len(search_results)])
        
        return jsonify(search_results[:5])
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify([])

@bp.route('/stock_analysis', methods=['POST'])
@login_required
def analyze_stock():
    try:
        # Get and validate form data
        ticker_input = request.form.get('ticker', '').split()[0].upper()
        
        # Debug print to see what's being received
        print("Form data received:", dict(request.form))
        
        # Convert lookback_days to int with validation
        try:
            lookback_days = int(request.form.get('lookback_days', 365))
            lookback_days = max(30, min(10000, lookback_days))
            print(f"Using lookback_days: {lookback_days}")  # Debug print
        except ValueError:
            lookback_days = 365
            print("Using default lookback_days: 365")
        
        crossover_days = int(request.form.get('crossover_days', 365))
        end_date = request.form.get('end_date')

        # Validate inputs
        if not ticker_input:
            raise ValueError("Ticker symbol is required")

        # Create visualization with explicit parameters
        fig = create_stock_visualization(
            ticker=ticker_input,
            end_date=end_date,
            lookback_days=lookback_days,  # Pass the validated lookback_days
            crossover_days=crossover_days
        )
        
        # Convert to HTML
        html_content = fig.to_html(
            full_html=True,
            include_plotlyjs=True,
            config={'responsive': True}
        )
        
        # Return response
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        return response
        
    except Exception as e:
        error_msg = f"Error analyzing {ticker_input}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return error_msg, 500