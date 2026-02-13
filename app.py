from flask import Flask
from routes import init_routes
import os

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialiser les routes
init_routes(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
