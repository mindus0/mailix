from flask import Flask
from routes import init_routes
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration de l'application
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 7  # 7 jours

# Configuration OAuth
app.config['GITHUB_CLIENT_ID'] = os.environ.get('GITHUB_CLIENT_ID')
app.config['GITHUB_CLIENT_SECRET'] = os.environ.get('GITHUB_CLIENT_SECRET')
app.config['GITLAB_CLIENT_ID'] = os.environ.get('GITLAB_CLIENT_ID')
app.config['GITLAB_CLIENT_SECRET'] = os.environ.get('GITLAB_CLIENT_SECRET')
app.config['BITBUCKET_CLIENT_ID'] = os.environ.get('BITBUCKET_CLIENT_ID')
app.config['BITBUCKET_CLIENT_SECRET'] = os.environ.get('BITBUCKET_CLIENT_SECRET')

# Configuration Baserow
app.config['BASEROW_API_URL'] = os.environ.get('BASEROW_API_URL')
app.config['BASEROW_TOKEN'] = os.environ.get('BASEROW_TOKEN')
app.config['BASEROW_TABLE_ID'] = os.environ.get('BASEROW_TABLE_ID')

# URLs de redirection
app.config['OAUTH_REDIRECT_BASE'] = os.environ.get('OAUTH_REDIRECT_BASE', 'http://localhost:5000')
app.config['DASHBOARD_URL'] = os.environ.get('DASHBOARD_URL', 'http://localhost:5000/dashboard')

# Vérification de la configuration
required_vars = ['SECRET_KEY', 'GITHUB_CLIENT_ID', 'GITHUB_CLIENT_SECRET', 
                 'GITLAB_CLIENT_ID', 'GITLAB_CLIENT_SECRET',
                 'BITBUCKET_CLIENT_ID', 'BITBUCKET_CLIENT_SECRET',
                 'BASEROW_API_URL', 'BASEROW_TOKEN', 'BASEROW_TABLE_ID']

missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    logger.warning(f"Variables d'environnement manquantes: {missing_vars}")

# Initialiser les routes
init_routes(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
