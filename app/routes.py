from flask import Blueprint, render_template, request, make_response, jsonify
from flask_login import login_required
from datetime import datetime
import yfinance as yf
import logging
import sys
import re
import os
import traceback
from app.utils.analyzer.stock_analyzer import create_stock_visualization
from sqlalchemy import inspect
from app import db 
from sqlalchemy import text 
from flask import send_file
import pandas as pd
import io
# Make sure this line is present
# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create Blueprint
bp = Blueprint('main', __name__)

def load_tickers():
    """Load tickers from TypeScript file"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, '..', 'tickers.ts')
        
        logger.debug(f"Current directory: {current_dir}")
        logger.debug(f"Looking for tickers.ts at: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"Tickers file not found at: {file_path}")
            file_path = os.path.join(os.getcwd(), 'tickers.ts')
            logger.debug(f"Trying current directory: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error("Tickers file not found in current directory either")
                return [], {}
        
        logger.info(f"Found tickers.ts at: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.debug(f"Read {len(content)} characters from tickers.ts")
            
        pattern = r'{[^}]*symbol:\s*"([^"]*)",[^}]*name:\s*"([^"]*)"[^}]*}'
        matches = re.finditer(pattern, content)
        
        TICKERS = []
        TICKER_DICT = {}
        
        for match in matches:
            symbol, name = match.groups()
            ticker_obj = {"symbol": symbol, "name": name}
            TICKERS.append(ticker_obj)
            TICKER_DICT[symbol] = name
        
        logger.info(f"Successfully loaded {len(TICKERS)} tickers")
        logger.debug(f"First few tickers: {TICKERS[:3]}")
        
        return TICKERS, TICKER_DICT
        
    except Exception as e:
        logger.error(f"Error loading tickers: {str(e)}")
        logger.error(traceback.format_exc())
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
            logger.info(f"Found exact match: {query}")
        
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
            logger.info(f"Found {len(partial_matches)} partial matches")
        
        # Sort results
        search_results.sort(key=lambda x: (
            x['symbol'] != query,
            len(x['symbol']),
            x['symbol']
        ))
        
        return jsonify(search_results[:5])
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify([])
@bp.route('/analyze', methods=['POST'])
@login_required
def analyze():
    try:
        # Get and validate form data
        ticker_input = request.form.get('ticker', '').split()[0].upper()
        lookback_days = int(request.form.get('lookback_days', 365))
        crossover_days = int(request.form.get('crossover_days', 365))
        end_date = request.form.get('end_date')

        # Log the received values
        logger.info(f"Analysis request - Ticker: {ticker_input}, Lookback: {lookback_days}, "
                   f"Crossover: {crossover_days}, End Date: {end_date}")
        
        # Validate inputs
        if not ticker_input:
            raise ValueError("Ticker symbol is required")
        
        # Validate lookback_days
        lookback_days = max(30, min(10000, lookback_days))
        
        # Validate crossover_days
        crossover_days = max(30, min(1000, crossover_days))
            
        # Create visualization
        fig = create_stock_visualization(
            ticker_input,
            end_date=end_date,
            lookback_days=lookback_days,
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
        error_html = f"""
        <html>
            <head>
                <title>Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 2rem; }}
                    .error {{ color: #dc3545; padding: 1rem; background-color: #f8d7da; 
                             border: 1px solid #f5c6cb; border-radius: 3px; }}
                    .back-link {{ margin-top: 1rem; display: block; }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h2>Analysis Error</h2>
                    <p>{error_msg}</p>
                </div>
                <a href="javascript:window.close();" class="back-link">Close Window</a>
            </body>
        </html>
        """
        return error_html, 500
# Keep your existing imports and code at the top

@bp.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get and validate form data
        ticker_input = request.form.get('ticker', '').split()[0].upper()
        lookback_days = int(request.form.get('lookback_days', 365))
        crossover_days = int(request.form.get('crossover_days', 365))
        end_date = request.form.get('end_date')

        # Log the received values
        logger.info(f"Analysis request - Ticker: {ticker_input}, Lookback: {lookback_days}, "
                   f"Crossover: {crossover_days}, End Date: {end_date}")
        
        # Validate inputs
        if not ticker_input:
            raise ValueError("Ticker symbol is required")
        
        # Validate lookback_days
        lookback_days = max(30, min(10000, lookback_days))
        
        # Validate crossover_days
        crossover_days = max(30, min(1000, crossover_days))
            
        # Create visualization
        fig = create_stock_visualization(
            ticker_input,
            end_date=end_date,
            lookback_days=lookback_days,
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
        error_html = f"""
        <html>
            <head>
                <title>Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 2rem; }}
                    .error {{ color: #dc3545; padding: 1rem; background-color: #f8d7da; 
                             border: 1px solid #f5c6cb; border-radius: 3px; }}
                    .back-link {{ margin-top: 1rem; display: block; }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h2>Analysis Error</h2>
                    <p>{error_msg}</p>
                </div>
                <a href="javascript:window.close();" class="back-link">Close Window</a>
            </body>
        </html>
        """
        return error_html, 500
# Add this new route with bp instead of main
# Add this import at the top@bp.route('/tables')
@bp.route('/tables')
@login_required
def tables():
    """Show database tables in document tree structure"""
    try:
        logger.info('Accessing database tables view')
        
        # Get all tables from database
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        logger.info(f'Found {len(tables)} tables in database')
        
        # Organize tables by type
        historical_tables = []
        financial_tables = []
        other_tables = []
        
        for table in tables:
            try:
                table_info = {
                    'name': table
                }
                
                if table.startswith('his_'):
                    ticker = table.replace('his_', '').upper()
                    historical_tables.append({
                        **table_info,
                        'ticker': ticker,
                        'type': 'Historical Data'
                    })
                    
                elif table.startswith('roic_'):
                    ticker = table.replace('roic_', '').upper()
                    financial_tables.append({
                        **table_info,
                        'ticker': ticker,
                        'type': 'Financial Data'
                    })
                    
                else:
                    other_tables.append({
                        **table_info,
                        'type': 'Other'
                    })
                    
            except Exception as table_error:
                logger.error(f"Error processing table {table}: {str(table_error)}")
                continue

        return render_template(
            'tables.html',
            historical_tables=historical_tables,
            financial_tables=financial_tables,
            other_tables=other_tables
        )
        
    except Exception as e:
        error_msg = f"Error fetching database tables: {str(e)}"
        logger.error(f"{error_msg}")
        return render_template('tables.html', error=error_msg)

@bp.route('/delete_table/<table_name>', methods=['POST'])
def delete_table(table_name):
    """Delete a table from database"""
    try:
        logger.info(f'Attempting to delete table: {table_name}')
        
        # Check if table exists
        inspector = inspect(db.engine)
        if table_name not in inspector.get_table_names():
            logger.error(f'Table {table_name} not found')
            return jsonify({'success': False, 'error': 'Table not found'}), 404

        # Use backticks to properly escape table name
        query = text(f'DROP TABLE `{table_name}`')
        db.session.execute(query)
        db.session.commit()
        
        logger.info(f'Successfully deleted table: {table_name}')
        return jsonify({'success': True, 'message': f'Table {table_name} deleted successfully'})
        
    except Exception as e:
        error_msg = f"Error deleting table {table_name}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': error_msg}), 500
@bp.route('/table-content/<table_name>')
def show_table_content(table_name):
    """Show the content of a specific table with sorting and pagination"""
    try:
        # Get sort parameters from URL
        sort_column = request.args.get('sort', 'Date')  # Default sort by Date
        sort_direction = request.args.get('direction', 'desc')  # Default descending
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)  # 50 items per page

        # Calculate offset
        offset = (page - 1) * per_page

        # Count total rows
        count_query = text(f'SELECT COUNT(*) FROM `{table_name}`')
        total_rows = db.session.execute(count_query).scalar()
        total_pages = (total_rows + per_page - 1) // per_page

        # Get all column names
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        # If sort column not in columns, use first column
        if sort_column not in columns and columns:
            sort_column = columns[0]

        # Build query with sorting and pagination
        query = text(f'''
            SELECT * FROM `{table_name}`
            ORDER BY `{sort_column}` {sort_direction}
            LIMIT :limit OFFSET :offset
        ''')
        
        # Execute query and fetch results
        result = db.session.execute(query, {'limit': per_page, 'offset': offset})
        
        # Convert results to list of dictionaries
        data = []
        for row in result:
            row_dict = {}
            for idx, col in enumerate(columns):
                row_dict[col] = row[idx]
            data.append(row_dict)
        
        return render_template(
            'table_content.html',
            table_name=table_name,
            columns=columns,
            data=data,
            current_page=page,
            total_pages=total_pages,
            per_page=per_page,
            sort_column=sort_column,
            sort_direction=sort_direction,
            total_rows=total_rows
        )
        
    except Exception as e:
        error_msg = f"Error fetching content for table {table_name}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return render_template('table_content.html', error=error_msg)


@bp.route('/export/<table_name>/<format>')
def export_table(table_name, format):
    """Export table data in CSV or Excel format"""
    try:
        # Get all data from table
        query = text(f'SELECT * FROM `{table_name}`')
        result = db.session.execute(query)
        
        # Get column names
        columns = result.keys()
        
        # Convert to DataFrame
        df = pd.DataFrame([dict(row) for row in result], columns=columns)
        
        # Create buffer for file
        buffer = io.BytesIO()
        
        if format == 'csv':
            # Export as CSV
            df.to_csv(buffer, index=False)
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'{table_name}.csv'
            )
            
        elif format == 'excel':
            # Export as Excel
            df.to_excel(buffer, index=False)
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{table_name}.xlsx'
            )
        
        else:
            return jsonify({'error': 'Unsupported format'}), 400
            
    except Exception as e:
        error_msg = f"Error exporting table {table_name}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500