# PlayerClient.py
import json
from fastapi import FastAPI
import requests

class PlayerClient:
    def __init__(self, name="PlayerClient"):
        self.name = name
        self.server_url = ""
        self.player_id = None
        self.app = FastAPI()
        self.register_routes()

    def get_id(self,server_url):
        self.server_url = server_url
        # Envoyer une requete pour s'enregistrer auprès du serveur et récupérer un player_id unique
        # on envoie son nom pour que le serveur puisse l'associer à l'id du joueur
        # si on dispode déjà d'un player_id enregistré localement, on peut l'envoyer au serveur pour récupérer les statistiques associées à ce player_id
        
        for i in range(3):
            resp = None
            if self.player_id:
                print(f"Player ID déjà enregistré localement : {self.player_id}. Envoi au serveur pour récupérer les statistiques associées.")
                resp = requests.post(f"{self.server_url}/register", json={"name": self.name, "player_id": self.player_id})
                break
            else: 
                resp = requests.post(f"{self.server_url}/register", json={"name": self.name})
                break
            if resp.status_code == 200:
                raise Exception(f"Erreur lors de l'enregistrement auprès du serveur : {resp.text}")
        data = resp.json()
        self.player_id = data.get("player_id")
        self.victoires = data.get("victoires", 0)
        self.défaites = data.get("défaites", 0)
        self.nuls = data.get("nuls", 0)
        print(f"Enregistré auprès du serveur avec player_id : {self.player_id}")

        return self.player_id
    
    def connect_to_server(self):
    
    def get_plateau_state(self, plateau_id):
        # Récupère l'état du plateau depuis le serveur sous forme d'un dictionnaire JSON 
        # le champ ids contient la liste des ids des joueur, 
        # un champ "loser_id" qui indique l'id du joueur qui a perdu (ou null si pas encore de perdant),
        # le champ plateau contient chacune des 61 cases du plateau :
        # un 0 pour les cases vides, 
        # un 1 pour les cases occupées par le joueur 1,
        # un 2 pour les cases occupées par le joueur 2,
        # un 3 pour les cases occupées par le joueur 3.
        # Exemple de réponse JSON :
        # {
        #   "ids": [123456, 789012],
        #   "loser_id": 789012,
        #   "plateau": [0, 0, 1, 2, 0, ..., 0]
        # }
        resp = requests.get(f"{self.server_url}/plateau/{plateau_id}")
        #vérifier que la requete a réussi
        if resp.status_code != 200:
            print("Erreur lors de la récupération de l'état du plateau :", resp.text)
            return None
        #convertir la réponse en dictionnaire Python
        return resp.json()

    def choose_move(self, plateau_state):
        pass # À implémenter : logique pour choisir un coup en fonction de l'état du plateau


    def new_game(self):
        #envoyer une requete pour démarrer une nouvelle partie
        resp = requests.post(f"{self.server_url}/new_game", json={"player_id": self.player_id})
        if resp.status_code == 200:
            print("Nouvelle partie démarrée avec succès !")
        else:
            print("Erreur lors du démarrage de la partie :", resp.text)
            
    def reset(self):
        self.victoires = 0
        self.défaites = 0
        self.nuls = 0

    def save_stats(self):
        # Enregistrer les statistiques localement (ex: dans un fichier)
        with open(f"{self.player_id}_stats.json", "w") as f:
            json.dump({"player_name": self.name, "player_id": self.player_id, "victoires": self.victoires, "défaites": self.défaites, "nuls": self.nuls}, f)
            

    def load_stats(self,file_path=None):
        # Charger les statistiques depuis un fichier
        if file_path is None:
             print("Aucun chemin de fichier fourni pour charger les statistiques. Utilisation du chemin par défaut.")
             self.reset()
        try:
            with open(file_path or f"{self.player_id}_stats.json", "r") as f:
                data = json.load(f)
                self.name = data.get("player_name", self.name)
                self.victoires = data.get("victoires", 0)
                self.défaites = data.get("défaites", 0)
                self.nuls = data.get("nuls", 0)
        except FileNotFoundError:
            self.reset()  # Si le fichier n'existe pas, on initialise les stats à zéro

    def register_routes(self):
        @self.app.post("/play")
        async def play_move(plateau_id: int):
            move=self.choose_move(self.get_plateau_state(plateau_id))
            return {"status": "ok", "plateau_id": plateau_id, "player_id": self.player_id, "move": move}

        @self.app.post("/lose")
        async def addLose(plateau_id: int):
            self.défaites += 1
            return {"status": "ok"}
        
        @self.app.post("/win")
        async def addWin(plateau_id: int):
            self.victoires += 1
            return {"status": "ok"}
        
        @self.app.post("/draw")
        async def addDraw(plateau_id: int):
            self.nuls += 1
            return {"status": "ok"}
        
        @self.app.get("/stats")
        async def get_stats():
            return {"player_name": self.name, "player_id": self.player_id, "victoires": self.victoires, "défaites": self.défaites, "nuls": self.nuls}
        
        @self.app.get("/reset")
        async def reset_stats():
            self.reset()
            return {"status": "ok"}
        
    def run(self, host="0.0.0.0", port=8001):
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)# Exemple d'utilisation
        
if __name__ == "__main__":
    client = PlayerClient(server_url="http://localhost:8000")
    client.play(plateau_id="abc123")