from flask import render_template, redirect, url_for, session
from functools import wraps
import os

# Simulation d'un décorateur login_required pour l'instant
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Pour l'instant, on simule que l'utilisateur n'est pas connecté
        # Plus tard, tu pourras implémenter la vraie logique d'authentification
        if not session.get('user_id'):
            return redirect(url_for('connect'))
        return f(*args, **kwargs)
    return decorated_function

def init_routes(app):
    
    # Routes publiques (accessibles sans authentification)
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
    
    # Routes protégées (nécessitent authentification)
    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/mindus_forge')
    @login_required
    def mindus_forge():
        return render_template('mindus_forge.html')
    
    # Route pour simuler le login (à remplacer plus tard)
    @app.route('/fake-login')
    def fake_login():
        session['user_id'] = 1
        return redirect(url_for('dashboard'))
    
    # Route pour simuler le logout
    @app.route('/fake-logout')
    def fake_logout():
        session.pop('user_id', None)
        return redirect(url_for('index'))
    
    # Gestionnaire d'erreur 404
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('index.html'), 404
