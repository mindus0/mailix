FROM python:3.9-slim

WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste de l'application
COPY . .

# Exposer le port
EXPOSE 5000

# Commande pour lancer l'application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
