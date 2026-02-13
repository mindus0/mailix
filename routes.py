from flask import render_template, redirect, url_for, session, request, jsonify, abort
from functools import wraps
import os
import requests
import secrets
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode
import json

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration OAuth
OAUTH_CONFIG = {
    'github': {
        'authorize_url': 'https://github.com/login/oauth/authorize',
        'token_url': 'https://github.com/login/oauth/access_token',
        'userinfo_url': 'https://api.github.com/user',
        'emails_url': 'https://api.github.com/user/emails',
        'scope': 'user:email',
        'client_id': None,
        'client_secret': None
    },
    'gitlab': {
        'authorize_url': 'https://gitlab.com/oauth/authorize',
        'token_url': 'https://gitlab.com/oauth/token',
        'userinfo_url': 'https://gitlab.com/api/v4/user',
        'scope': 'read_user',
        'client_id': None,
        'client_secret': None
    },
    'bitbucket': {
        'authorize_url': 'https://bitbucket.org/site/oauth2/authorize',
        'token_url': 'https://bitbucket.org/site/oauth2/access_token',
        'userinfo_url': 'https://api.bitbucket.org/2.0/user',
        'emails_url': 'https://api.bitbucket.org/2.0/user/emails',
        'scope': 'account email',
        'client_id': None,
        'client_secret': None
    }
}

def generate_state_token():
    """Génère un token d'état pour la sécurité OAuth"""
    return secrets.token_urlsafe(32)

def validate_state_token(state):
    """Valide le token d'état de la session"""
    saved_state = session.pop('oauth_state', None)
    if not saved_state or saved_state != state:
        return False
    return True

def login_required(f):
    """Décorateur pour protéger les routes qui nécessitent une authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            session['next_url'] = request.url
            return redirect(url_for('connect'))
        return f(*args, **kwargs)
    return decorated_function

def get_baserow_headers():
    """Retourne les headers pour l'API Baserow"""
    from flask import current_app
    return {
        'Authorization': f"Token {current_app.config['BASEROW_TOKEN']}",
        'Content-Type': 'application/json'
    }

def find_user_by_platform_id(platform, platform_id):
    """Recherche un utilisateur dans Baserow par sa plateforme et son ID"""
    from flask import current_app
    
    try:
        url = current_app.config['BASEROW_API_URL'].replace(
            str(current_app.config['BASEROW_TABLE_ID']), 
            current_app.config['BASEROW_TABLE_ID']
        )
        
        # Construire l'URL de recherche
        params = {
            'filters__ID_Plateforme__equal': platform_id,
            'filters__Plateforme__equal': platform
        }
        
        response = requests.get(
            url,
            headers=get_baserow_headers(),
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            return results[0] if results else None
        else:
            logger.error(f"Erreur recherche utilisateur: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception recherche utilisateur: {str(e)}")
        return None

def create_or_update_user(user_data, platform):
    """Crée ou met à jour un utilisateur dans Baserow"""
    from flask import current_app
    
    try:
        # Vérifier si l'utilisateur existe déjà
        existing_user = find_user_by_platform_id(platform, user_data.get('platform_id'))
        
        # URL de l'API Baserow
        base_url = current_app.config['BASEROW_API_URL']
        
        # Préparer les données pour Baserow
        baserow_data = {
            'Email': user_data.get('email', ''),
            'Nom': user_data.get('name', user_data.get('username', '')),
            'Pseudo': user_data.get('username', ''),
            'Plateforme': platform,
            'ID_Plateforme': user_data.get('platform_id', ''),
            'Avatar_URL': user_data.get('avatar_url', ''),
            'Profil_URL': user_data.get('profile_url', ''),
            'Access_Token': user_data.get('access_token', ''),
            'Refresh_Token': user_data.get('refresh_token', ''),
            'Derniere_Connexion': datetime.utcnow().isoformat(),
            'Est_Actif': True
        }
        
        # Ajouter la date de création si c'est un nouvel utilisateur
        if not existing_user:
            baserow_data['Date_Creation'] = datetime.utcnow().isoformat()
        
        if existing_user:
            # Mise à jour
            row_id = existing_user['id']
            update_url = f"{base_url}/{row_id}/"
            
            response = requests.patch(
                update_url,
                headers=get_baserow_headers(),
                json=baserow_data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erreur mise à jour Baserow: {response.status_code} - {response.text}")
                return existing_user
        else:
            # Création
            response = requests.post(
                base_url,
                headers=get_baserow_headers(),
                json=baserow_data
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Erreur création Baserow: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Exception Baserow: {str(e)}")
        return None

def get_user_email(platform, access_token):
    """Récupère l'email de l'utilisateur depuis la plateforme"""
    try:
        if platform == 'github':
            emails_response = requests.get(
                OAUTH_CONFIG['github']['emails_url'],
                headers={'Authorization': f'token {access_token}'}
            )
            if emails_response.status_code == 200:
                emails = emails_response.json()
                # Chercher l'email principal
                for email in emails:
                    if email.get('primary') and email.get('verified'):
                        return email.get('email')
                # Sinon prendre le premier email vérifié
                for email in emails:
                    if email.get('verified'):
                        return email.get('email')
                        
        elif platform == 'bitbucket':
            emails_response = requests.get(
                OAUTH_CONFIG['bitbucket']['emails_url'],
                headers={'Authorization': f'Bearer {access_token}'}
            )
            if emails_response.status_code == 200:
                emails = emails_response.json().get('values', [])
                for email in emails:
                    if email.get('is_primary') and email.get('is_confirmed'):
                        return email.get('email')
                        
        return None
        
    except Exception as e:
        logger.error(f"Erreur récupération email {platform}: {str(e)}")
        return None

def init_routes(app):
    """Initialise toutes les routes de l'application"""
    
    # Configuration OAuth avec les valeurs de l'application
    OAUTH_CONFIG['github']['client_id'] = app.config['GITHUB_CLIENT_ID']
    OAUTH_CONFIG['github']['client_secret'] = app.config['GITHUB_CLIENT_SECRET']
    OAUTH_CONFIG['gitlab']['client_id'] = app.config['GITLAB_CLIENT_ID']
    OAUTH_CONFIG['gitlab']['client_secret'] = app.config['GITLAB_CLIENT_SECRET']
    OAUTH_CONFIG['bitbucket']['client_id'] = app.config['BITBUCKET_CLIENT_ID']
    OAUTH_CONFIG['bitbucket']['client_secret'] = app.config['BITBUCKET_CLIENT_SECRET']
    
    # Routes publiques
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/terme')
    def terme():
        return render_template('terme.html')
    
    @app.route('/privacy')
    def privacy():
        return render_template('privacy.html')
    
    @app.route('/notice')
    def notice():
        return render_template('notice.html')
    
    @app.route('/about')
    def about():
        return render_template('about.html')
    
    @app.route('/pricing')
    def pricing():
        return render_template('pricing.html')
    
    @app.route('/connect')
    def connect():
        return render_template('conect.html')
    
    # Routes OAuth
    @app.route('/auth/<platform>')
    def oauth_login(platform):
        """Redirige vers la plateforme OAuth pour l'authentification"""
        if platform not in OAUTH_CONFIG:
            abort(404)
        
        # Générer un état pour la sécurité
        state = generate_state_token()
        session['oauth_state'] = state
        
        # Construire l'URL de redirection
        config = OAUTH_CONFIG[platform]
        redirect_uri = f"{app.config['OAUTH_REDIRECT_BASE']}/auth/{platform}/callback"
        
        params = {
            'client_id': config['client_id'],
            'redirect_uri': redirect_uri,
            'scope': config['scope'],
            'state': state,
            'response_type': 'code'
        }
        
        # Paramètres supplémentaires pour certaines plateformes
        if platform == 'bitbucket':
            params['response_type'] = 'code'
        
        auth_url = f"{config['authorize_url']}?{urlencode(params)}"
        
        logger.info(f"Redirection OAuth {platform}: {auth_url}")
        return redirect(auth_url)
    
    @app.route('/auth/<platform>/callback')
    def oauth_callback(platform):
        """Callback après authentification OAuth"""
        if platform not in OAUTH_CONFIG:
            abort(404)
        
        # Vérifier les paramètres
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            logger.error(f"Erreur OAuth {platform}: {error}")
            return redirect(url_for('connect', error=error))
        
        if not code:
            logger.error(f"Pas de code OAuth pour {platform}")
            return redirect(url_for('connect', error='no_code'))
        
        # Valider l'état
        if not validate_state_token(state):
            logger.error(f"État OAuth invalide pour {platform}")
            return redirect(url_for('connect', error='invalid_state'))
        
        try:
            config = OAUTH_CONFIG[platform]
            redirect_uri = f"{app.config['OAUTH_REDIRECT_BASE']}/auth/{platform}/callback"
            
            # Échanger le code contre un token
            token_data = {
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'code': code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            headers = {'Accept': 'application/json'}
            
            # Format spécifique pour Bitbucket
            if platform == 'bitbucket':
                token_response = requests.post(
                    config['token_url'],
                    data=token_data,
                    headers=headers,
                    auth=(config['client_id'], config['client_secret'])
                )
            else:
                token_response = requests.post(
                    config['token_url'],
                    data=token_data,
                    headers=headers
                )
            
            if token_response.status_code != 200:
                logger.error(f"Erreur récupération token {platform}: {token_response.text}")
                return redirect(url_for('connect', error='token_error'))
            
            token_json = token_response.json()
            access_token = token_json.get('access_token')
            refresh_token = token_json.get('refresh_token')
            
            if not access_token:
                logger.error(f"Pas de token d'accès pour {platform}")
                return redirect(url_for('connect', error='no_token'))
            
            # Récupérer les informations de l'utilisateur
            if platform == 'bitbucket':
                user_response = requests.get(
                    config['userinfo_url'],
                    headers={'Authorization': f'Bearer {access_token}'}
                )
            else:
                user_response = requests.get(
                    config['userinfo_url'],
                    headers={'Authorization': f'token {access_token}'}
                )
            
            if user_response.status_code != 200:
                logger.error(f"Erreur récupération user {platform}: {user_response.text}")
                return redirect(url_for('connect', error='userinfo_error'))
            
            user_info = user_response.json()
            
            # Extraire les données selon la plateforme
            user_data = {}
            
            if platform == 'github':
                user_data = {
                    'platform_id': str(user_info.get('id')),
                    'username': user_info.get('login'),
                    'name': user_info.get('name'),
                    'avatar_url': user_info.get('avatar_url'),
                    'profile_url': user_info.get('html_url'),
                    'access_token': access_token,
                    'refresh_token': refresh_token
                }
                # Récupérer l'email
                user_data['email'] = get_user_email(platform, access_token)
                
            elif platform == 'gitlab':
                user_data = {
                    'platform_id': str(user_info.get('id')),
                    'username': user_info.get('username'),
                    'name': user_info.get('name'),
                    'email': user_info.get('email'),
                    'avatar_url': user_info.get('avatar_url'),
                    'profile_url': user_info.get('web_url'),
                    'access_token': access_token,
                    'refresh_token': refresh_token
                }
                
            elif platform == 'bitbucket':
                user_data = {
                    'platform_id': user_info.get('uuid'),
                    'username': user_info.get('username'),
                    'name': user_info.get('display_name'),
                    'avatar_url': user_info.get('links', {}).get('avatar', {}).get('href'),
                    'profile_url': user_info.get('links', {}).get('html', {}).get('href'),
                    'access_token': access_token,
                    'refresh_token': refresh_token
                }
                # Récupérer l'email
                user_data['email'] = get_user_email(platform, access_token)
            
            # Créer ou mettre à jour l'utilisateur dans Baserow
            baserow_user = create_or_update_user(user_data, platform)
            
            if baserow_user:
                # Stocker les informations dans la session
                session['user_id'] = baserow_user.get('id')
                session['user_email'] = user_data.get('email')
                session['user_name'] = user_data.get('name', user_data.get('username'))
                session['user_platform'] = platform
                session['user_avatar'] = user_data.get('avatar_url')
                session['logged_in'] = True
                session.permanent = True
                
                logger.info(f"Connexion réussie: {user_data.get('email')} via {platform}")
                
                # Rediriger vers le dashboard
                return redirect(app.config['DASHBOARD_URL'])
            else:
                logger.error(f"Erreur sauvegarde Baserow pour {platform}")
                return redirect(url_for('connect', error='database_error'))
                
        except Exception as e:
            logger.error(f"Exception OAuth {platform}: {str(e)}")
            return redirect(url_for('connect', error='server_error'))
    
    @app.route('/auth/logout')
    def logout():
        """Déconnexion"""
        session.clear()
        return redirect(url_for('index'))
    
    # Routes protégées
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Page dashboard après connexion"""
        user_info = {
            'email': session.get('user_email'),
            'name': session.get('user_name'),
            'platform': session.get('user_platform'),
            'avatar': session.get('user_avatar')
        }
        return render_template('dashboard.html', user=user_info)
    
    @app.route('/mindus_forge')
    @login_required
    def mindus_forge():
        return render_template('mindus_forge.html')
    
    # Route pour vérifier l'état de la session (API)
    @app.route('/api/session-status')
    def session_status():
        """Vérifie si l'utilisateur est connecté"""
        return jsonify({
            'logged_in': session.get('logged_in', False),
            'user': {
                'email': session.get('user_email'),
                'name': session.get('user_name'),
                'platform': session.get('user_platform'),
                'avatar': session.get('user_avatar')
            } if session.get('logged_in') else None
        })
    
# Route pour All Projects
@app.route('/all_project')
@login_required
def all_project():
    """Page de tous les projets de l'utilisateur"""
    # Récupérer les informations utilisateur de la session
    user_info = {
        'email': session.get('user_email'),
        'name': session.get('user_name'),
        'platform': session.get('user_platform'),
        'avatar': session.get('user_avatar')
    }
    return render_template('all_project.html', user=user_info)

# Route pour API Keys
@app.route('/api-keys')
@login_required
def api_keys():
    """Page de gestion des clés API"""
    user_info = {
        'email': session.get('user_email'),
        'name': session.get('user_name'),
        'platform': session.get('user_platform'),
        'avatar': session.get('user_avatar')
    }
    return render_template('api_keys.html', user=user_info)

# Route pour Documentation
@app.route('/documentation')
@login_required
def documentation():
    """Page de documentation"""
    user_info = {
        'email': session.get('user_email'),
        'name': session.get('user_name'),
        'platform': session.get('user_platform'),
        'avatar': session.get('user_avatar')
    }
    return render_template('documentation.html', user=user_info)

# Route pour API Documentation
@app.route('/api-docs')
@login_required
def api_docs():
    """Page de documentation API"""
    user_info = {
        'email': session.get('user_email'),
        'name': session.get('user_name'),
        'platform': session.get('user_platform'),
        'avatar': session.get('user_avatar')
    }
    return render_template('api_docs.html', user=user_info)
