import copy
import hashlib
import random
import os
import time
import datetime
import torch
import torch.nn as nn
import torch.optim as optim
from Yavalath import player
from Yavalath import human_player



class YavalathNN(nn.Module):
    def __init__(self, input_size=61*4, output_size=61, hidden_size=128):
        super(YavalathNN, self).__init__()
        
        self.fc1 = nn.Linear(input_size, hidden_size*2)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(0.3)
        
        self.fc2 = nn.Linear(hidden_size*2, hidden_size)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(0.3)
        
        self.fc3 = nn.Linear(hidden_size, hidden_size // 2)
        self.relu3 = nn.ReLU()
        self.dropout3 = nn.Dropout(0.2)
        
        self.output = nn.Linear(hidden_size // 2, output_size)
        
    def forward(self, x):
        x = self.relu1(self.fc1(x))
        x = self.dropout1(x)
        
        x = self.relu2(self.fc2(x))
        x = self.dropout2(x)
        
        x = self.relu3(self.fc3(x))
        x = self.dropout3(x)
        
        x = self.output(x)
        return x
    
    # --- Nouvelles méthodes de gestion du modèle ---
    def save_model(self, filepath="yavalath_model.pth"):
        torch.save(self.state_dict(), filepath)
        print(f"Modèle sauvegardé dans {filepath}")

    def load_model(self, filepath="yavalath_model.pth"):
        if os.path.exists(filepath):
            self.load_state_dict(torch.load(filepath))
            print(f"Modèle chargé depuis {filepath}")
            self.eval() # Important pour désactiver le Dropout en mode jeu
        else:
            print(f"Fichier {filepath} non trouvé. Le modèle reste tel quel (aléatoire ou précédent).")


# Initialiser le modèle
model = YavalathNN()
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

class AI_Player(player):

    def __init__(self, model_path=None, train_mode=False,model=None, player_id=None, color=None):
        if not color :
            color="red"
        #génère un hash pour générer un id unique
        super().__init__(id(self), color)
        if model is not None:
            self.model = model
        elif model_path:
            self.model = YavalathNN()
            self.model.load_model(model_path)
        else:
            self.model = YavalathNN()
        #else:
            #print(f"Joueur {player_id}: Modèle initialisé aléatoirement.")

        self.train_mode = train_mode
        if self.train_mode:
            self.model.train()
        else:
            self.model.eval()

    def save(self, filename):
        self.model.save_model(filename)

    def jouer(self, plateau):
        move=self.choisir_case(plateau)
        if plateau.jouer_coup(move, self):
            self.mémoriser_case(plateau, move)
        return move
    
    def choisir_case(self, plateau):
        state=[]
        #attribuer un état à chaque case qui sera utilisé comme entrée pour chaque noeud du réseau de neurones
        #parcourir le dictionnaire plateau.get_all_cases() dans l'ordre des clés (de la plus petite à la plus grande)
        #ajouter 0 à la case si elle est vide, -1 si elle est occupée par soi-même, l'ID du joueur si elle est occupée par un autre joueur
        state+=plateau.legal_moves()
        state+=self.get_my_cases()
        # Canaux 3 et 4 : Adversaires (ordonnés par ID pour être déterministe)
        other_players = [p for p in plateau.players if p.get_id() != self.get_id()]
        other_players.sort(key=lambda p: p.get_id())  # Ordre déterministe !
        
        for p in other_players:
            state += list(plateau.get_case_occupied_by(p))
        
        # Padding si moins de 2 adversaires (partie à 2 joueurs)
        while len(state) < 61 * 4:
            state += [False] * 61
        # plateau_cases=plateau.sorted_cases_id
        # for case_id in plateau_cases:
        #     case = plateau.get_case_by_id(case_id)
        #     if case.is_empty():
        #         state.append(0)
        #     elif case.ennemy_of(self):
        #         state.append(case.get_player_id())
        #     else:
        #         state.append(-1)
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0)  # Ajouter une dimension batch
        # En mode jeu (eval), on désactive le calcul des gradients pour aller plus vite
        # En mode train, on les garde (bien que pour l'inférence simple ici ce ne soit pas critique, c'est utile pour l'apprentissage futur)
        if self.train_mode:
             output = self.model(state_tensor)
        else:
            with torch.no_grad():
                output = self.model(state_tensor)
        
        # Masquage
        # tableau des coups légaux (True légal/False illégal)
        legal_moves = plateau.legal_moves()
        #atributer -inf aux sorties correspondant aux coups illégaux
        for idx, legal in enumerate(legal_moves):
            if not legal:
                output[0][idx] = float('-inf')
        
        

        # Exploration vs Exploitation (Epsilon-Greedy - utile pour l'entraînement)
        # Si on entraîne, parfois on joue au hasard pour découvrir de nouveaux coups
        if self.train_mode and random.random() < 0.1:
            # legal_moves est une liste de booléens
            legal_indices = [idx for idx, is_legal in enumerate(legal_moves) if is_legal]
            if legal_indices:
                action_index = random.choice(legal_indices)
            else:
                action_index = torch.argmax(output, dim=1).item()
        else:
            action_index = torch.argmax(output, dim=1).item()
            
        move = plateau.sorted_cases_id[action_index]
        return move
    
class EvolutionTrainer:
    def __init__(self, population_size=10, mutation_rate=0.02, sigma=0.1, autorate=False):
        self.population_size = population_size
        self.mutation_rate = mutation_rate # Probabilité qu'un poids mute
        self.sigma = sigma # Force de la mutation
        self.generation = 0
        self.population = [] 
        self.best_model = None
        self.autorate = autorate
    def initialize_population(self, checkpoint="AI/best.pth"):
        """Crée une population. Si un checkpoint existe, on part de lui."""
        self.population = []
        
        start_model = YavalathNN()
        
        if os.path.exists(checkpoint):
            print(f"Reprise de l'entraînement depuis {checkpoint}...")
            start_model.load_model(checkpoint)
            # Le premier de la liste est le champion exact
            self.population.append(start_model)
            
            # Les autres sont des variants mutés de ce champion
            # Cela permet de continuer à explorer autour de la meilleure solution connue
            print(f"Génération de {self.population_size - 1} variants...")
            for _ in range(self.population_size - 1):
                mutant = self.mutate(start_model)
                self.population.append(mutant)
        else:
            print(f"Aucun checkpoint trouvé. Initialisation aléatoire de {self.population_size} IA...")
            self.population.append(start_model) # Le premier est aléatoire
            for _ in range(self.population_size - 1):
                model = YavalathNN()
                self.population.append(model)
        self.players = [AI_Player(model=model, train_mode=False) for model in self.population]
        for player in self.players:
            player.reset()

    def mutate(self, model):
        """Crée une copie mutée d'un modèle"""
        child = copy.deepcopy(model)
        child_state = child.state_dict()
        if self.autorate:
            self.mutation_rate = min(1 / (self.generation/10), 1) if self.generation > 0 else 1
            self.sigma = min(1 / (self.generation/10), 1) if self.generation > 0 else 1
        with torch.no_grad():
            for param_key in child_state:
                # On récupère le tenseur de poids
                param_tensor = child_state[param_key]
                # On crée un masque de mutation (quels poids vont changer ?)
                mask = torch.rand_like(param_tensor) < self.mutation_rate
                # On génère du bruit gaussien
                noise = torch.randn_like(param_tensor) * self.sigma
                # On applique le bruit seulement là où le masque est True
                child_state[param_key] += mask * noise
        
        child.load_state_dict(child_state)
        return child

    def evaluate_match(self, p1, p2, p3):
        """Joue un match entre trois modèles et retourne le gagnant (1, 2, 3, 0 si nul)"""
        
        # On lance la partie (il faut modifier légèrement Yavalath pour qu'il ne fasse pas de print/input bloquants)
        # Idéalement, play_game devrait retourner l'ID du gagnant sans input utilisateur
        self.plateau.new_game([p1, p2], parties=1, display=False, pondération=4)
        self.plateau.new_game([p2, p1], parties=1, display=False, pondération=4) 
        # On fait jouer des parties déjà commencées pour éviter l'overfitting
        self.plateau.new_game([p1, p2], parties=1, display=False, coups_aleatoires=4) 
        self.plateau.new_game([p2, p1], parties=1, display=False, coups_aleatoires=4) 
        # choisi un 3ème joueur aléatoire pour mélanger les choses avec un ordre aléatoire
        for order in [[p1, p2, p3], [p3, p1, p2], [p2, p3, p1]]:
            self.plateau.new_game(order, parties=1, display=False, pondération=2)

        # Ce morceau dépend de comment new_game stocke le résultat
        # Supposons qu'on regarde les wins
        # if p1.wins > p2.wins: return model_a
        # if p2.wins > p1.wins: return model_b
        # return None # Match nul

    def run_generation(self, plateau_cls):
        """Fait jouer la population en tournoi"""
        self.plateau=plateau_cls()
        self.generation += 1
        print(f"--- Génération {self.generation} ---")
        
        random.shuffle(self.players)
        
        
        # Tournoi : on prend les IA par paires
        # on fait jouer chaque IA contre toutes les autres
        for i in range(len(self.players)):
            for j in range(i + 1, len(self.players)):
                p1 = self.players[i]
                p2 = self.players[j]
                # ajout d'un 3ème joueur dans la liste pour avoir une partie à 3 joueurs
                p3 = random.choice(self.players)
                # On fait jouer le match
                self.evaluate_match(p1, p2, p3)
                

        # 3. Tri par score accumulé
        self.players.sort(key=lambda p: p.wins, reverse=True)
        # Sélection des meilleurs
        num_selected = max(2, int(self.population_size*0.2)) # On garde au moins 2
        selected_models = [p for p in self.players[:num_selected]] 
        #ajoutés à la prochaine génération
        next_gen = list(selected_models)
        # Sauvegarde du meilleur modèle
        self.best_model = next_gen[0].model
        self.best_model.save_model(f"AI/best.pth")
        print(f"Meilleur score cette génération : {next_gen[0].wins} victoires.")
        # Réinitialisation des scores des joueurs sélectionnés et génération suivante

        for player in next_gen:
            player.reset() # Réinitialisation des scores
        # Génération de mutants pour remplir 1/5 de la population
        while len(next_gen) < int(self.population_size*0.6):
            parent = random.choice(selected_models)
            child = self.mutate(parent.model)
            joueur_child = AI_Player(model=child, train_mode=False)
            joueur_child.reset()
            next_gen.append(joueur_child)
        # Remplissage aléatoire pour le reste
        while len(next_gen) < self.population_size:
            joueur_nouveau = AI_Player(train_mode=False,model=YavalathNN())
            joueur_nouveau.reset()
            next_gen.append(joueur_nouveau)
        # Mise à jour de la population
        self.players = next_gen[:self.population_size] # On s'assure de garder la taille fixe
        #destruction des joueurs temporaires
        # Sauvegarde du "champion" temporaire (le premier de la liste par exemple)

# --- Modification nécessaire dans votre classe Yavalath.py ---
# Il faut que new_game puisse s'exécuter sans intervention humaine (pas de input())
# et qu'elle soit rapide (pas de plt.pause trop longs si on veut entraîner vite).

if __name__ == "__main__":
    from Yavalath import Yavalath

    auto=True  # Mettre à False pour voir les démonstrations
    if not auto:
        random_player = AI_Player(model=YavalathNN(), train_mode=False) # Modèle aléatoire par défaut
        random_player.color="blue"
                    
    print("Démarrage de l'entraînement...")
    
    # 1. Configuration de l'entraîneur
    # population_size=20 : 20 IA différentes vont s'affronter
    # mutation_rate=0.05 : 5% de chance qu'un poids change lors d'une mutation
    trainer = EvolutionTrainer(population_size=20, mutation_rate=0.05, sigma=0.1, autorate=True)
    
    # 2. Création de la première génération (aléatoire)
    trainer.initialize_population()
    # --- CONFIGURATION DE L'HEURE DE FIN ---
    HEURE_ARRET = 13     # Heure (0-23)
    MINUTE_ARRET = 0   # Minutes (0-59)
    # ---------------------------------------
    
    now = datetime.datetime.now()
    stop_time = now.replace(hour=HEURE_ARRET, minute=MINUTE_ARRET, second=0, microsecond=0)

    # Si l'heure cible est déjà passée aujourd'hui (ex: il est 23h, on veut arrêter à 7h), c'est pour demain
    if stop_time < now:
        stop_time += datetime.timedelta(days=1)

    print(f"--> Objectif : Arrêt programmé pour {stop_time.strftime('%d/%m à %H:%M')}")
    print("    (Le script finira la génération en cours avant de couper)")
    gen = 0
    start_global = time.time()
    
    # 3. Boucle d'entraînement
    try:
        # On lance 50 générations (vous pouvez augmenter ce chiffre)
        while datetime.datetime.now() < stop_time:
            trainer.run_generation(Yavalath)
            gen += 1
            
            # Affichage du temps restant estimé
            remaining = stop_time - datetime.datetime.now()
            # On formate proprement le timedelta (enlève les microsecondes)
            remaining_str = str(remaining).split('.')[0] 
            print(f"    [Temps restant avant arrêt : {remaining_str}]")
            
            # --- Sauvegarde régulière de sécurité ---
            if gen % 5 == 0:
                trainer.best_model.save_model(f"trainning/{gen}.pth")

            # (Optionnel) Tous les 10 tours, on fait jouer le champion contre un random pour voir
            if (gen + 1) % 10 == 0:
                if not auto:
                    print(f"\n--- Match de démonstration (Gen {gen+1}) ---")
                    champion_model = trainer.best_model
                    
                    # Le champion joue contre une IA aléatoire (fraîchement créée)
                    champ_player = AI_Player(model=champion_model, train_mode=False)

                    #random_player = human_player(2, "blue")
                
                    plateau_demo = Yavalath()
                    # On affiche ce match pour que vous puissiez voir les progrès (display=True)
                    plateau_demo.new_game([champ_player, random_player], parties=1, display=True)
                    print("--- Fin de la démonstration ---\n")

    except KeyboardInterrupt:
        print("\nEntraînement interrompu par l'utilisateur.")
        print(f"\nHeure limite atteinte ou interruption.")
    print(f"Total : {gen} générations entraînées.")
    print("Entraînement terminé.")
    # Sauvegarde finale du meilleur modèle
    if trainer.players:
        trainer.players[0].model.save_model("AI/champion_final.pth")