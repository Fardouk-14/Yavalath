# SmartPlayer.py
from Yavalath import player, Yavalath
from random import choice

class SmartPlayer(player):
    def __init__(self, id, color):
        super().__init__(id, color)
    
    def jouer(self, plateau):
        best_move = self.evaluate_best_move(plateau)
        if plateau.jouer_coup(best_move, self):
            self.mémoriser_case(plateau, best_move)
        return best_move
    
    def evaluate_best_move(self, plateau):
        legal_ids = plateau.get_empty_cases()
        if not legal_ids:
            return None
        
        best_score = float('-inf')
        best_moves = []
        
        for case_id in legal_ids:
            score = self.evaluate_move(plateau, case_id)
            if score > best_score:
                best_score = score
                best_moves = [case_id]
            elif score == best_score:
                best_moves.append(case_id)
        
        return choice(best_moves)  # Random parmi les meilleurs
    
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
        
        # 4. Vérifie si on force l'adversaire à faire 3 (piège)
        # TODO: Plus complexe, nécessite simulation
        
        # 5. Bonus pour les positions centrales
        score += self.centrality_bonus(q, r)
        
        # 6. Bonus pour créer des menaces (2 en ligne avec espace)
        score += self.count_threats(plateau, q, r) * 10
        
        # 7. Malus pour les positions adjacentes à nos pions (risque de 3)
        score -= self.adjacent_own_risk(plateau, q, r) * 5
        
        return score
    
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