from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
import bcrypt
import uuid
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# Configuration de la connexion à la base de données PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL', "dbname='jeux_olympiques' user='pierrechevin' host='localhost' password='Elsalvador60?' port='5432'")

try:
    conn = psycopg2.connect(DATABASE_URL)
    print("Connecté à la base de données PostgreSQL avec succès")
except Exception as e:
    print(f"Erreur lors de la connexion à la base de données PostgreSQL: {e}")

@app.route('/')
def home():
    return "Bienvenue à l'API Jeux Olympiques!"

@app.route('/api/endpoint', methods=['GET', 'POST'])
def endpoint():
    if request.method == 'GET':
        return jsonify({"message": "GET reçu"}), 200
    elif request.method == 'POST':
        data = request.json
        return jsonify({"message": "POST reçu", "data": data}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # Vérifier si les champs requis sont présents
    if not email or not password:
        return jsonify({"status": "error", "message": "Email et mot de passe sont requis"}), 400

    try:
        cur = conn.cursor()
        cur.execute("SELECT email, mot_de_passe FROM administrateur WHERE email = %s", (email,))
        admin = cur.fetchone()
        cur.close()

        if admin:
            print(f"Admin trouvé : {admin[0]}")
        else:
            print("Admin non trouvé")

        if admin and bcrypt.checkpw(password.encode('utf-8'), admin[1].encode('utf-8')):
            return jsonify({"status": "success", "message": "Authentification réussie"}), 200
        else:
            return jsonify({"status": "error", "message": "Email ou mot de passe incorrect"}), 401

    except Exception as e:
        print(f"Erreur lors de la connexion à la base de données PostgreSQL: {e}")
        return jsonify({"status": "error", "message": "Erreur interne du serveur"}), 500


@app.route('/login_user', methods=['POST'])
def login_user():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # Vérifier si les champs requis sont présents
    if not email or not password:
        return jsonify({"status": "error", "message": "Email et mot de passe sont requis"}), 400

    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, mot_de_passe FROM utilisateur WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:
            print(f"User found: ID = {user[0]}, Email = {user[1]}")
        else:
            print("User not found")

        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            return jsonify({"status": "success", "message": "Authentification réussie", "user_id": user[0]}), 200
        else:
            return jsonify({"status": "error", "message": "Email ou mot de passe incorrect"}), 401

    except Exception as e:
        print(f"Erreur lors de la connexion à la base de données PostgreSQL: {e}")
        return jsonify({"status": "error", "message": "Erreur interne du serveur"}), 500


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    nom = data.get('nom')
    prenom = data.get('prenom')
    email = data.get('email')
    mot_de_passe = data.get('mot_de_passe')

    # Log the received data
    print(f"Data received: nom={nom}, prenom={prenom}, email={email}, mot_de_passe={mot_de_passe}")

    # Vérifier si les champs requis sont présents
    if not nom or not prenom or not email or not mot_de_passe:
        print("Missing required fields")
        return jsonify({"status": "error", "message": "Tous les champs sont requis"}), 400

    try:
        print(f"Tentative de création de compte pour {nom} {prenom} avec email {email}")

        # Hacher le mot de passe
        hashed_password = bcrypt.hashpw(mot_de_passe.encode('utf-8'), bcrypt.gensalt())
        print(f"Mot de passe haché : {hashed_password}")

        # Générer une clé UUID et la convertir en chaîne de caractères
        user_key = str(uuid.uuid4())

        # Insérer l'utilisateur dans la base de données
        cur = conn.cursor()
        cur.execute("INSERT INTO utilisateur (nom, prenom, email, mot_de_passe, clef) VALUES (%s, %s, %s, %s, %s)",
                    (nom, prenom, email, hashed_password.decode('utf-8'), user_key))
        conn.commit()
        cur.close()

        print("Compte créé avec succès")
        return jsonify({"status": "success", "message": "Compte créé avec succès"}), 201

    except Exception as e:
        print(f"Erreur lors de la création du compte: {e}")
        conn.rollback()  # Annuler la transaction en cas d'erreur
        return jsonify({"status": "error", "message": "Erreur interne du serveur"}), 500
    

@app.route('/offers', methods=['GET'])
def get_offers():
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nom, description, prix, nombre_personnes FROM offre")
        offers = cur.fetchall()
        cur.close()

        # Formater les résultats sous forme de liste de dictionnaires
        offers_list = []
        for offer in offers:
            offers_list.append({
                "id": offer[0],
                "nom": offer[1],
                "description": offer[2],
                "prix": offer[3],
                "nombre_personnes": offer[4]
            })

        return jsonify({"status": "success", "offers": offers_list}), 200

    except Exception as e:
        print(f"Erreur lors de la récupération des offres: {e}")
        return jsonify({"status": "error", "message": "Erreur interne du serveur"}), 500



@app.route('/payment', methods=['POST'])
def process_payment():
    data = request.json
    utilisateur_id = data.get('utilisateur_id')
    panier = data.get('panier')  # Panier est une liste d'objets avec offer_id et quantite

    if not utilisateur_id or not panier:
        return jsonify({"status": "error", "message": "Données de paiement manquantes"}), 400

    try:
        cur = conn.cursor()

        # Récupérer la clé de l'utilisateur
        cur.execute("SELECT clef FROM utilisateur WHERE id = %s", (utilisateur_id,))
        clef_utilisateur = cur.fetchone()[0]

        # Calculer le total de la commande
        total = 0
        for item in panier:
            cur.execute("SELECT prix FROM offre WHERE id = %s", (item['offer_id'],))
            prix = cur.fetchone()[0]
            total += prix * item['quantite']

        # Générer une clé de commande unique
        clef_commande_unique = str(uuid.uuid4())

        # Concaténer les clés pour obtenir la clé finale de la commande
        clef_commande_finale = clef_utilisateur + clef_commande_unique

        # Insérer la commande dans la table commande
        cur.execute(
            "INSERT INTO commande (utilisateur_id, date_commande, total, clef_commande) VALUES (%s, NOW(), %s, %s) RETURNING id",
            (utilisateur_id, total, clef_commande_finale)
        )
        commande_id = cur.fetchone()[0]

        # Insérer chaque offre de la commande dans la table commande_offre
        for item in panier:
            cur.execute(
                "INSERT INTO commande_offre (commande_id, offre_id, quantite) VALUES (%s, %s, %s)",
                (commande_id, item['offer_id'], item['quantite'])
            )

        # Générer le QR code à partir de la clé de commande
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(clef_commande_finale)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_code_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # Insérer le e-ticket dans la table e_ticket
        cur.execute(
            "INSERT INTO e_ticket (utilisateur_id, commande_id, clef_finale, qr_code) VALUES (%s, %s, %s, %s)",
            (utilisateur_id, commande_id, clef_commande_finale, qr_code_image)
        )

        conn.commit()
        cur.close()

        return jsonify({
            "status": "success",
            "message": "Paiement traité avec succès",
            "clef_commande": clef_commande_finale,
            "qr_code": qr_code_image
        }), 201

    except Exception as e:
        conn.rollback()
        print(f"Erreur lors du traitement du paiement: {e}")
        return jsonify({"status": "error", "message": "Erreur interne du serveur"}), 500
    


@app.route('/admin/offers', methods=['GET'])
def get_admin_offers():
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nom, description, prix, nombre_personnes FROM offre")
        offers = cur.fetchall()
        cur.close()

        offers_list = []
        for offer in offers:
            offers_list.append({
                "id": offer[0],
                "name": offer[1],
                "description": offer[2],
                "prix": offer[3],
                "capacity": offer[4]
            })

        return jsonify({"status": "success", "offers": offers_list}), 200

    except Exception as e:
        print(f"Erreur lors de la récupération des offres: {e}")
        return jsonify({"status": "error", "message": "Erreur interne du serveur"}), 500



@app.route('/admin/offers', methods=['POST'])
def create_offer():
    data = request.json
    nom = data.get('name')
    description = data.get('description')
    prix = data.get('prix')
    nombre_personnes = data.get('capacity')

    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO offre (nom, description, prix, nombre_personnes) VALUES (%s, %s, %s, %s) RETURNING id", 
                    (nom, description, prix, nombre_personnes))
        offer_id = cur.fetchone()[0]
        conn.commit()
        cur.close()

        return jsonify({"status": "success", "message": "Offre créée avec succès", "id": offer_id}), 201

    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de la création de l'offre: {e}")
        return jsonify({"status": "error", "message": "Erreur interne du serveur"}), 500


@app.route('/admin/offers/<int:id>', methods=['PUT'])
def update_offer(id):
    data = request.json
    nom = data.get('name')
    description = data.get('description')
    prix = data.get('prix')
    nombre_personnes = data.get('capacity')

    try:
        cur = conn.cursor()
        cur.execute("UPDATE offre SET nom = %s, description = %s, prix = %s, nombre_personnes = %s WHERE id = %s",
                    (nom, description, prix, nombre_personnes, id))
        conn.commit()
        cur.close()

        return jsonify({"status": "success", "message": "Offre mise à jour avec succès"}), 200

    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de la mise à jour de l'offre: {e}")
        return jsonify({"status": "error", "message": "Erreur interne du serveur"}), 500


@app.route('/admin/offers/<int:id>', methods=['DELETE'])
def delete_offer(id):
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM offre WHERE id = %s", (id,))
        conn.commit()
        cur.close()

        return jsonify({"status": "success", "message": "Offre supprimée avec succès"}), 200

    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de la suppression de l'offre: {e}")
        return jsonify({"status": "error", "message": "Erreur interne du serveur"}), 500


@app.route('/admin/commandes', methods=['GET'])
def get_admin_commandes():
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                c.id AS commande_id,
                u.id AS utilisateur_id,
                u.nom AS utilisateur_nom,
                o.id AS offre_id,
                o.nom AS offre_nom,
                co.quantite AS quantite,
                c.clef_commande
            FROM
                commande c
            JOIN
                commande_offre co ON c.id = co.commande_id
            JOIN
                offre o ON co.offre_id = o.id
            JOIN
                utilisateur u ON c.utilisateur_id = u.id
            ORDER BY
                c.id;
        """)
        rows = cur.fetchall()
        cur.close()

        # Formater les résultats sous forme de liste de dictionnaires
        commandes_list = []
        for row in rows:
            commandes_list.append({
                "commande_id": row[0],
                "utilisateur_id": row[1],
                "utilisateur_nom": row[2],
                "offre_id": row[3],
                "offre_nom": row[4],
                "quantite": row[5],
                "clef_commande": row[6]
            })

        return jsonify({"status": "success", "commandes": commandes_list}), 200

    except Exception as e:
        print(f"Erreur lors de la récupération des commandes: {e}")
        return jsonify({"status": "error", "message": "Erreur interne du serveur"}), 500



if __name__ == '__main__':
    app.run(port=3002)









