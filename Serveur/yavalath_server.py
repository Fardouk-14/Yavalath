#yavalath_server.py
#serveur pour le jeu Yavalath, gère les parties, les joueurs et les règles du jeu
#Utilise Flask pour créer une API REST qui permet aux clients de se connecter, de récupérer l'état du jeu
#le serveur gère également la logique du jeu, vérifie les coups légaux, met à jour l'état du plateau et détermine les gagnants
#c'est le serveur qui demande aux clients de jouer en leur envoyant l'id du plateau, l'état du plateau et en attendant leur réponse avec le coup choisi
#le serveur envoi l'information de victoire ou de défaite à tous les clients connectés à la partie lorsque celle-ci se termine
#le serveur peut gérer plusieurs parties simultanément et permet à des clients de se connecter et de jouer à tout moment
#le serveur peut gére un matchmaking pour trouver des adversaires pour les joueurs qui veulent jouer en ligne
#le serveur peut également stocker les statistiques des joueurs, comme le nombre de victoires, de défaites et de parties jouées dans une base de données SQLite ou un fichier JSON

import os
import random
from fastapi import requests
from flask import Flask, request, jsonify
from Yavalath import Yavalath
import uuid
import sqlite3

caracters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890'
def generate_random_name(length=6):
    return ''.join(random.choice(caracters) for _ in range(length))

class YavalathServer:
    def __init__(self):
        self.app = Flask(__name__)
        self.plateaux = {}  # Dictionnaire pour stocker les plateaux de jeu, clé : plateau_id, valeur : instance de Yavalath
        self.register_routes()
        self.connected_players = {}  # Dictionnaire pour stocker les joueurs connectés, clé : player_id, valeur : informations du joueur
        self.matchmaking_queue = []  # Liste pour gérer le matchmaking des joueurs qui veulent jouer en ligne
        #si le fichier de db n'existe pas, le créer et initialiser la table des statistiques
        db_file = 'yavalath_stats.db'
        db_init = os.path.exists(db_file)
        self.db_connection = sqlite3.connect('yavalath_stats.db')
        if not db_init:
            self.initialize_db()

    def initialize_db(self):
        cursor = self.db_connection.cursor()
        cursor.execute('''
            CREATE TABLE players (
                player_id TEXT PRIMARY KEY,
                player_name TEXT NOT NULL,
                victories INTEGER DEFAULT 0,
                defeats INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                last_ip TEXT,
                last_active TIMESTAMP,
                connected BOOLEAN DEFAULT 0,
                UNIQUE(player_id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE game_history (
                game_id TEXT PRIMARY KEY,
                player1_id TEXT NOT NULL,
                player2_id TEXT NOT NULL,
                player3_id TEXT,
                winner_id TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY(player1_id) REFERENCES players(player_id),
                FOREIGN KEY(player2_id) REFERENCES players(player_id),
                FOREIGN KEY(player3_id) REFERENCES players(player_id),
                FOREIGN KEY(winner_id) REFERENCES players(player_id)
                unique(game_id)
            );'''
        )
        cursor.execute('''
            CREATE TABLE running_games (
                game_id TEXT PRIMARY KEY,
                player1_id TEXT NOT NULL,
                player2_id TEXT NOT NULL,
                player3_id TEXT,
                start_time TIMESTAMP,
                FOREIGN KEY(player1_id) REFERENCES players(player_id),
                FOREIGN KEY(player2_id) REFERENCES players(player_id),
                FOREIGN KEY(player3_id) REFERENCES players(player_id)
                unique(game_id)
            );
            '''
        )
        self.db_connection.commit()    
    def isUnknown(self, player_id):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
        existing_player = cursor.fetchone()
        return existing_player is None
    
    def ask_player_to_play(self, plateau_id, player_id):
        # Cette méthode est appelée par les instances de ServerPlayer pour demander au serveur de récupérer le coup du joueur
        # Le serveur envoie une requete au client correspondant pour lui demander de jouer, en lui fournissant l'état actuel du plateau
        # Le serveur attend ensuite la réponse du client avec le coup choisi et retourne ce coup à la méthode jouer() du ServerPlayer
        reqst = requests.post(f"{self.server_url}/ask_move", json={"plateau_id": plateau_id, "player_id": player_id})


    def register_routes(self):
        @self.app.route('/register', methods=['POST'])
        def register():
            data = request.get_json()
            name = data.get("name", None)
            if not name:
                #génère un nom aléatoire si aucun nom n'est fourni
                name = generate_random_name()
            player_id = data.get("player_id", uuid.uuid4().hex)  # Génère un player_id unique si aucun n'est fourni
            
            # Si un player_id est fourni, on vérifie s'il existe déjà dans la base de données
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
            existing_player = cursor.fetchone()
            if existing_player:
                # Si le player_id existe, on retourne les statistiques associées
                return jsonify({
                    "player_id": existing_player[0],
                    "player_name": existing_player[1],
                    "victoires": existing_player[2],
                    "défaites": existing_player[3],
                    "nuls": existing_player[4]
                })
            else:
                # Si le player_id n'existe pas, on enregistre un nouveau joueur avec ce player_id
                cursor.execute("INSERT INTO players (player_id, player_name, victories, defeats, draws) VALUES (?, ?, 0, 0, 0)", (player_id, name))
                self.db_connection.commit()
                return jsonify({"player_id": player_id, "player_name": name, "victoires": 0, "défaites": 0, "nuls": 0}), 200
            
        @self.app.route('/new_game', methods=['POST'])
        def new_game():
            data = request.get_json()
            player_id = data.get("player_id")
            if not player_id:
                return jsonify({"error": "Player ID is required"}), 400
            if self.isUnknown(player_id):
                return jsonify({"error": "Player unknown"}), 400
                     
            
            
            plateau_id = str(uuid.uuid4())  # Génère un identifiant unique pour le plateau
            self.plateaux[plateau_id] = {'jeu': Yavalath(), 'players': [], 'loser': None, 'board': [None] * 61}  # Crée une nouvelle instance de Yavalath pour ce plateau
            self.plateaux[plateau_id]['players'].append(player_id)  # Ajoute le joueur à la liste des joueurs du plateau
            
            return jsonify({"plateau_id": plateau_id}), 200

        @self.app.route('/plateau/<plateau_id>', methods=['GET'])
        def get_plateau(plateau_id):
            plateau = self.plateaux.get(plateau_id)
            if not plateau:
                return jsonify({"error": "Plateau not found"}), 404
            
            # Convertir l'état du plateau en format JSON
            plateau_state = {
                "ids": [player.player_id for player in plateau.players],
                "loser_id": plateau.loser.player_id if plateau.loser else None,
                "plateau": [0] * 61  # Remplir avec les valeurs appropriées (0, 1, 2, 3)
            }
            for i, cell in enumerate(plateau.board):
                if cell is not None:
                    plateau_state["plateau"][i] = cell.player_id + 1  # +1 car les joueurs sont codés à partir de 1 dans le plateau
            
            return jsonify(plateau_state)

    def run(self):
        self.app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    server = YavalathServer()
    server.run()