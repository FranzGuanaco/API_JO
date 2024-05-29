# Utiliser l'image de base python
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier le fichier des exigences
COPY requirements.txt requirements.txt

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le contenu du projet dans le conteneur
COPY . .

# Définir la variable d'environnement pour Flask
ENV FLASK_APP=app.py

# Exposer le port 8080
EXPOSE 8080

# Commande pour exécuter l'application
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]

