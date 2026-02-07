# SmartPlayer.py
from Yavalath import player, Yavalath, make_grid
from random import choice
from PlayerClient import PlayerClient

class SmartPlayer(PlayerClient):
    def __init__(self, server_url, name="SmartBot", difficulty=5):
        super().__init__(server_url, name=f"{name}_d{difficulty}")
        self.difficulty = difficulty
        self.grid,self.cases_by_id,self.cases_by_coord = make_grid()  # Pour les évaluations de coups
    
    # Override de choose_move pour utiliser notre IA heuristique
    def choose_move(self, plateau_state):
        best_move = self.choisir_coup(self.evaluate_best_move(plateau_state))
        return best_move
    
    def choisir_coup(self, coups):
        """Choisit le coup avec le meilleur score."""
        if not coups:
            return None
        max_score = max(coups.values())
        best_moves = [move for move, score in coups.items() if score == max_score]
        
        return choice(best_moves)

    def evaluate_best_move(self, plateau_state, recursion_depth=None, joueur_id=None,first_call=True):
        if joueur_id is None:
            joueur_id = self.player_id
        # plateau_state est un dictionnaire avec les clés 'ids' et 'plateau' :
        # le champ ids contient la liste des ids des joueurs, 
        # le champ "loser_id" qui indique l'id du joueur qui a perdu (ou null si pas encore de perdant),
        # le champ plateau contient chacune des 61 cases du plateau :
        # un 0 pour les cases vides, 
        # un 1 pour les cases occupées par le joueur 1 (premier id dans ids),
        # un 2 pour les cases occupées par le joueur 2 (deuxième id dans ids),
        # un 3 pour les cases occupées par le joueur 3 (troisième id dans ids).
        if recursion_depth is None:
            recursion_depth = self.difficulty
        # Récupérer les coups légaux
        legal_ids = [case_id for case_id in self.grid if plateau_state['plateau'][self.grid.index(case_id)] == 0]
        if not legal_ids:
            return {}
        
        coups = {}
        for case_id in legal_ids:
            coups[case_id] = self.evaluate_move(plateau_state, case_id)
        
        # Condition d'arrêt
        if recursion_depth <= 0:
            return coups
        
        top_moves = coups.items()
        # Évaluer en profondeur seulement les meilleurs coups (pour la vitesse)
        if not first_call:
            top_moves = sorted(coups.items(), key=lambda x: x[1], reverse=True)[:5]

        
        for move, base_score in top_moves:
            if base_score <= -10000 or base_score >= 10000:
                continue  # Pas besoin de simuler victoire/défaite immédiate
            score_ajouté = 0
            # Simuler le coup en dupliquant le dictionnaire de l'état du plateau
            new_plateau = {key: value for key, value in plateau_state.items()}
            # copie le plateau 
            new_plateau['plateau'] = new_plateau['plateau'][:]
            new_plateau['ids'] = new_plateau['ids'][:]
            new_plateau['loser_id'] = new_plateau['loser_id']
            # Trouver notre index de joueur
            player_index = new_plateau['ids'].index(joueur_id)
            # Simuler notre coup
            new_plateau['plateau'][self.grid.index(move)] = player_index + 1  # +1 car les joueurs sont codés à partir de 1 dans le plateau
            # décaler les ids pour me retrouver en position 0
            joueurs = new_plateau['ids'][player_index:] + new_plateau['ids'][:player_index]
            # supprimer mon id de la liste ainsi que les losers
            joueurs_en_jeu = [j for j in joueurs if j != joueur_id and j != new_plateau['loser_id']]



            # on simule un tour des adversaires
            for j in joueurs_en_jeu:
                # Simuler les coups futurs dans la partie
                adv_coups = self.evaluate_best_move(new_plateau, recursion_depth - 1, joueur_id=j, first_call=False)
                if adv_coups:
                    # on récupère le meilleur coup de l'adversaire
                    # On suppose que l'adversaire joue son meilleur coup, donc on prend le score négatif de ce coup
                    # on applique une pondération pour ne pas surévaluer les coups futurs
                    score_ajouté = - max(adv_coups.values()) /3.0
                    #on joue le coup de l'adversaire pour simuler la partie
                    best_adv = max(adv_coups, key=adv_coups.get)
                    new_plateau['plateau'][self.grid.index(best_adv)] = new_plateau['ids'].index(j) + 1  # +1 car les joueurs sont codés à partir de 1 dans le plateau
                    # vérifier si l'adversaire a perdu via son score 
                    if score_ajouté <= 10000/3.0:
                        if new_plateau['loser_id'] is None and len(joueurs_en_jeu) > 1:
                            new_plateau['loser_id'] = j  # Simuler la défaite de cet adversaire
                        else:
                            score_ajouté = 10000/2.0  # Si un adversaire a déjà perdu, on considère que c'est une victoire pour nous
                    
            #on ajoute le score ajouté à notre score de base pour ce coup
            coups[move] += score_ajouté
            
        return coups
    
    def evaluate_move(self, plateau_state, case_id, playerid=None):
        if playerid is None:
            playerid = self.player_id
        """Évalue un coup potentiel. Score élevé = bon coup."""
        case = self.cases_by_id.get(case_id)
        q, r = case.get_coordonnées()
        score = 0
        
        # 1. Vérifie si ce coup nous fait PERDRE (3 en ligne)
        if self.creates_line(plateau_state, q, r, playerid, 3):
            return -10000  # Éviter à tout prix
        
        # 2. Vérifie si ce coup nous fait GAGNER (4 en ligne)
        if self.creates_line(plateau_state, q, r, playerid, 4):
            return 10000  # Victoire immédiate
        
        # 3. Vérifie si on bloque une victoire adverse (4 en ligne ennemi)
        for p in plateau_state['players']:
            if p != playerid:
                if self.creates_line(plateau_state, q, r, p, 4):
                    score += 5000  # Bloquer victoire adverse

        # 3.5 Bloquer un 3 adverse (les forcer à perdre)
        for p in plateau_state['players']:
            if p != playerid:
                if self.creates_line(plateau, q, r, p, 3):
                    score += 100  # Moins prioritaire que bloquer 4
        
        # 4. Bonus pour les positions centrales
        score += self.centrality_bonus(q, r)
        
        # 5. Bonus pour créer des lignes potentielles (2 alignés SANS faire 3)
        score += self.safe_line_bonus(plateau, q, r) * 50
        
        # 6. Bonus pour créer des menaces (2 en ligne avec espace pour 4)
        score += self.count_threats(plateau, q, r) * 50
        
        # 7. Malus SEULEMENT si ça risque de forcer un 3 (pas juste adjacent)
        # SUPPRIMÉ: adjacent_own_risk était trop pénalisant
        
        return score
    
    def safe_line_bonus(self, plateau, q, r):
        """Bonus pour créer 2 en ligne qui peuvent devenir 4 sans passer par 3."""
        bonus = 0
        directions = [(1, 0), (0, 1), (-1, 1)]
        
        for dq, dr in directions:
            # Compter nos pions et cases vides dans cette direction
            my_count = 1  # La case qu'on joue
            empty_before = 0
            empty_after = 0
            
            # Direction positive
            for step in range(1, 4):
                nq, nr = q + dq * step, r + dr * step
                next_case = plateau.cases_by_coord.get((nq, nr))
                if next_case is None:
                    break
                if next_case.player == self:
                    my_count += 1
                elif next_case.is_empty():
                    empty_after += 1
                else:
                    break
            
            # Direction négative
            for step in range(1, 4):
                nq, nr = q - dq * step, r - dr * step
                next_case = plateau.cases_by_coord.get((nq, nr))
                if next_case is None:
                    break
                if next_case.player == self:
                    my_count += 1
                elif next_case.is_empty():
                    empty_before += 1
                else:
                    break
            
            # 2 pions alignés avec assez d'espace pour faire 4 = bon
            # Mais on vérifie qu'on ne sera pas forcé de faire 3
            if my_count == 2 and (empty_before + empty_after) >= 2:
                bonus += 1
            # 1 pion adjacent avec espace = construction de ligne
            elif my_count == 1 and (empty_before >= 1 and empty_after >= 1):
                # Case adjacente à un de nos pions avec espace des deux côtés
                adj_count = self.count_adjacent_own(plateau, q, r)
                if adj_count == 1:  # Exactement 1 pion adjacent = bon début de ligne
                    bonus += 0.5
        
        return bonus
    
    def count_adjacent_own(self, plateau, q, r):
        """Compte les pions adjacents à nous."""
        directions = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
        count = 0
        for dq, dr in directions:
            nq, nr = q + dq, r + dr
            next_case = plateau.cases_by_coord.get((nq, nr))
            if next_case and next_case.player == self:
                count += 1
        return count    
    
    def plateau_simulé(self, plateau, move):
        """Copie le plateau et joue le coup."""
        import copy
        new_plateau = Yavalath()
        
        # Copier l'état des cases
        for case_id, case_obj in plateau.cases_by_id.items():
            if case_obj.player is not None:
                # Trouver le joueur correspondant
                player_id = case_obj.player.get_id()
                new_plateau.cases_by_id[case_id].player = case_obj.player
        
        new_plateau.mask_legal = plateau.mask_legal.copy()
        new_plateau.coups = plateau.coups
        new_plateau.players = plateau.players  # Garder les mêmes références !
        
        # Jouer le coup
        new_plateau.jouer_coup(move, self)
        
        return new_plateau

    def evaluate_move_for(self, plateau, case_id, target_player):
        """Évalue un coup pour un joueur spécifique."""
        case = plateau.get_case_by_id(case_id)
        q, r = case.get_coordonnées()
        
        if self.creates_line(plateau, q, r, target_player, 3):
            return -10000
        if self.creates_line(plateau, q, r, target_player, 4):
            return 10000
        
        return self.centrality_bonus(q, r)  # Simple évaluation 
    

    def creates_line(self, plateau, q, r, target_player, length):
        """Vérifie si jouer en (q,r) crée une ligne de 'length' pour target_player."""
        directions = [(1, 0), (0, 1), (-1, 1)]
        
        for dq, dr in directions:
            count = 1  # La case qu'on joue
            
            # Direction positive
            step = 1
            while step <= 3:
                nq, nr = q + dq * step, r + dr * step
                next_case = plateau.cases_by_coord.get((nq, nr))
                if next_case and next_case.player == target_player:
                    count += 1
                    step += 1
                else:
                    break
            
            # Direction négative
            step = 1
            while step <= 3:
                nq, nr = q - dq * step, r - dr * step
                next_case = plateau.cases_by_coord.get((nq, nr))
                if next_case and next_case.player == target_player:
                    count += 1
                    step += 1
                else:
                    break
            
            if count >= length:
                return True
        
        return False
    
    def centrality_bonus(self, q, r):
        """Cases centrales valent plus."""
        # Distance au centre (0,0)
        dist = abs(q) + abs(r) + abs(-q - r)
        return max(0, 8 - dist)  # Plus c'est central, plus c'est haut
    
    def count_threats(self, plateau, q, r):
        """Compte les menaces créées (2 alignés avec espace pour 4)."""
        threats = 0
        directions = [(1, 0), (0, 1), (-1, 1)]
        
        for dq, dr in directions:
            my_count = 1
            empty_count = 0
            
            for sign in [1, -1]:
                for step in range(1, 4):
                    nq, nr = q + sign * dq * step, r + sign * dr * step
                    next_case = plateau.cases_by_coord.get((nq, nr))
                    if next_case is None:
                        break
                    if next_case.player == self:
                        my_count += 1
                    elif next_case.is_empty():
                        empty_count += 1
                    else:
                        break
            
            # 2 pions + 2 espaces = menace potentielle
            if my_count == 2 and empty_count >= 2:
                threats += 1
        
        return threats
    
    def adjacent_own_risk(self, plateau, q, r):
        """Compte les pions adjacents à nous (risque de 3 accidentel)."""
        directions = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
        risk = 0
        
        for dq, dr in directions:
            nq, nr = q + dq, r + dr
            next_case = plateau.cases_by_coord.get((nq, nr))
            if next_case and next_case.player == self:
                risk += 1
        
        return risk


if __name__ == "__main__":
    from Yavalath import Yavalath, human_player, RobotPlayer
    
    plateau = Yavalath()
    smart = SmartPlayer(1, "#00b500")
    human = human_player(2, "#0000b5")
    # robot = RobotPlayer(3, "#b50000")
    
    plateau.new_game([smart, human], parties=3, display=True)