#server_player.py
# ce fichier défini une classe de joueur de Yavalath qui sert d'interface entre le serveur et le moteur de jeu Yavalath. 
# Cette classe peut être utilisée pour implémenter un joueur qui communique avec le serveur pour récupérer l'état du plateau et envoyer ses coups.
from Yavalath import Yavalath, player
class ServerPlayer(player):
    def __init__(self, player_id, color,server_parent,plateau_id):
        self.player_id = player_id
        self.color = color
        self.server_parent = server_parent  # Référence au serveur pour communiquer avec lui
        self.plateau_id = plateau_id

    def get_id(self):
        return self.player_id
    
    def get_color(self):
        return self.color
    
    def jouer(self, plateau):
        move=self.server_parent.ask_player_to_play(self.plateau_id, self.player_id)  # Demande au serveur de récupérer le coup du joueur
        return move
