from flask import Flask, request, jsonify, render_template, redirect
import sqlite3
import string
import random
import os
from datetime import datetime

app = Flask(__name__)

# Database setup
def get_db_connection():
    conn = sqlite3.connect('urls.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Generate a random short code
def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        conn = get_db_connection()
        existing = conn.execute('SELECT id FROM urls WHERE short_code = ?', (code,)).fetchone()
        conn.close()
        if not existing:
            return code

# Home route - serve the frontend
@app.route('/')
def home():
    return render_template('index.html')

# API endpoint to shorten URL
@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    try:
        data = request.get_json()
        original_url = data.get('url')
        
        if not original_url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Validate URL
        if not original_url.startswith(('http://', 'https://')):
            original_url = 'https://' + original_url
        
        # Generate short code
        short_code = generate_short_code()
        
        # Save to database
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO urls (short_code, original_url) VALUES (?, ?)',
            (short_code, original_url)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'short_code': short_code,
            'short_url': f"{request.host_url}{short_code}"
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Redirect route - visit short URL
@app.route('/<short_code>')
def redirect_to_url(short_code):
    conn = get_db_connection()
    url_data = conn.execute(
        'SELECT original_url FROM urls WHERE short_code = ?',
        (short_code,)
    ).fetchone()
    conn.close()
    
    if url_data:
        # Increment click count (optional)
        conn = get_db_connection()
        conn.execute(
            'UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?',
            (short_code,)
        )
        conn.commit()
        conn.close()
        return redirect(url_data['original_url'])
    else:
        return "URL not found", 404

# (Optional) Stats endpoint - view all URLs
@app.route('/stats')
def stats():
    conn = get_db_connection()
    urls = conn.execute('SELECT * FROM urls ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('stats.html', urls=urls)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)