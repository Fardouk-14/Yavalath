# SmartPlayer.py
from Yavalath import player, Yavalath
from random import choice

class SmartPlayer(player):
    def __init__(self, id, color, difficulty=5):
        super().__init__(id, color)
        self.difficulty = difficulty
    
    def jouer(self, plateau):
        best_move = self.choisir_coup(self.evaluate_best_move(plateau))
        if plateau.jouer_coup(best_move, self):
            self.mémoriser_case(plateau, best_move)
        return best_move
    def choisir_coup(self, coups):
        """Choisit le coup avec le meilleur score."""
        if not coups:
            return None
        max_score = max(coups.values())
        best_moves = [move for move, score in coups.items() if score == max_score]
        
        return choice(best_moves)

    def evaluate_best_move(self, plateau, recursion_depth=None):
        if recursion_depth is None:
            recursion_depth = self.difficulty
        legal_ids = plateau.get_empty_cases()
        if not legal_ids:
            return {}
        
        coups = {}
        for case_id in legal_ids:
            coups[case_id] = self.evaluate_move(plateau, case_id)
        
        # Condition d'arrêt
        if recursion_depth <= 0:
            return coups
        
        # Évaluer en profondeur seulement les meilleurs coups (pour la vitesse)
        top_moves = sorted(coups.items(), key=lambda x: x[1], reverse=True)[:5]
        
        for move, base_score in top_moves:
            if base_score <= -10000 or base_score >= 10000:
                continue  # Pas besoin de simuler victoire/défaite immédiate
            
            # Simuler le coup
            new_plateau = self.plateau_simulé(plateau, move)
            
            # Simuler réponse adversaire (meilleur coup)
            for p in new_plateau.players:
                if p.get_id() != self.get_id() and not p.has_lost:
                    adv_coups = {}
                    for adv_move in new_plateau.get_empty_cases():
                        adv_coups[adv_move] = self.evaluate_move_for(new_plateau, adv_move, p)
                    if adv_coups:
                        best_adv = max(adv_coups, key=adv_coups.get)
                        new_plateau.jouer_coup(best_adv, p)
                        # Copier l'état du joueur simulé
                        break
            
            # Récursion
            future_scores = self.evaluate_best_move(new_plateau, recursion_depth - 1)
            if future_scores:
                future = max(future_scores.values())
                coups[move] = base_score + future * 0.5  # Pondération
        
        return coups
    
    def evaluate_move(self, plateau, case_id):
        """Évalue un coup potentiel. Score élevé = bon coup."""
        case = plateau.get_case_by_id(case_id)
        q, r = case.get_coordonnées()
        score = 0
        
        # 1. Vérifie si ce coup nous fait PERDRE (3 en ligne)
        if self.creates_line(plateau, q, r, self, 3):
            return -10000  # Éviter à tout prix
        
        # 2. Vérifie si ce coup nous fait GAGNER (4 en ligne)
        if self.creates_line(plateau, q, r, self, 4):
            return 10000  # Victoire immédiate
        
        # 3. Vérifie si on bloque une victoire adverse (4 en ligne ennemi)
        for p in plateau.players:
            if p != self:
                if self.creates_line(plateau, q, r, p, 4):
                    score += 5000  # Bloquer victoire adverse

        # 3.5 Bloquer un 3 adverse (les forcer à perdre)
        for p in plateau.players:
            if p != self:
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