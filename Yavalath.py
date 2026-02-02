import matplotlib.pyplot as plt
from random import choice


def graycode(n):
    return n ^ (n >> 1)
def gray_to_binary(g):
    n = g
    shift = 1
    while (g >> shift) > 0:
        n ^= (g >> shift)
        shift += 1
    return n


class case:
    def __init__(self, q, r, id):
        self.q = q
        self.r = r
        self.id = id
        #numréo du joueur occupant la case None si inoccupée
        self.player=None
    def get_coordonnées(self):
        return (self.q, self.r)
    def get_id(self):
        if self.id is not None:
            return self.id
    def is_empty(self):
        return self.player is None
    def is_occupied(self):
        return self.player is not None
    def ennemy_of(self, player):
        return self.is_occupied() and self.player != player
    
    def get_player_id(self):
        if self.is_occupied():
            return self.player.get_id()
        return None

    def get_an_id(q,r):
        q_offset = q + 4
        r_offset = r + 4
        gray_q = graycode(q_offset)
        gray_r = graycode(r_offset)
        return (gray_q << 4) | gray_r
    
    def est_adjacente(self, autre_case):
        dq = abs(self.q - autre_case.q)
        dr = abs(self.r - autre_case.r)
        ds = abs((-self.q - self.r) - (-autre_case.q - autre_case.r))
        return (dq <= 1 and dr <= 1 and ds <= 1) and (dq + dr + ds == 2)
        
    def coordonnées_vers_id(self, q, r):
        if self.q == q and self.r == r:
            return self.id
        else:
            return None
    def get_adjacentes_id(self):
        adjacentes = []
        directions = [(1,0), (0,1), (-1,1), (-1,0), (0,-1), (1,-1)]
        for dq, dr in directions:
            q_adj = self.q + dq
            r_adj = self.r + dr
            if -4 <= q_adj <= 4 and -4 <= r_adj <= 4 and -4 <= -q_adj - r_adj <= 4:
                adj_id = case.get_an_id(q_adj, r_adj)
                adjacentes.append(adj_id)
        return adjacentes

class player:
    def __init__(self, id, color):
        self.id = id
        self.color = color
        self.has_lost = False
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.has_won = False
    
    def get_id(self):
        return self.id
    
    def get_color(self):
        return self.color
    
    def set_lost(self):
        if not self.has_lost:
            self.has_lost = True
            self.losses += 1
    def set_won(self):
        if not self.has_won:
            self.has_won = True
            self.wins += 1
    #retourne un ID de coup à jouer
    def jouer(self, plateau):
        return None

class human_player(player):
    def __init__(self, id, color):
        super().__init__(id, color)
    
    def jouer(self,plateau):
        # Si une fenêtre graphique est active, on privilégie le clic
        if plateau.fig is not None and plt.fignum_exists(plateau.fig.number):
            print(f"Joueur {self.id} ({self.color}), CLIQUEZ sur une case dans la fenêtre...")
            plt.figure(plateau.fig.number) # Focus sur la fenêtre
            
            while True:
                # show_clicks=False évite de dessiner une croix temporaire moche
                # timeout=-1 attend indéfiniment
                pts = plt.ginput(1, timeout=-1, show_clicks=False, mouse_add=1, mouse_stop=3, mouse_pop=2)
                
                if not pts:
                    print("Sélection annulée ou fenêtre fermée.")
                    # Fallback clavier si le clic échoue
                    break 
                
                clic_x, clic_y = pts[0]
                
                # Trouver la case la plus proche du clic
                closest_case = None
                # Rayon au carré max pour accepter le clic (pour ne pas cliquer entre les cases)
                # Un hexagone a un rayon ~0.5, dist² ~0.25
                min_sq_dist = 0.4 
                
                for case in plateau.cases_by_id.values():
                    q, r = case.get_coordonnées()
                    # Coordonnées visuelles (les mêmes que dans afficher_plateau)
                    cx = q + r/2
                    cy = r * (3**0.5/2)
                    
                    dist_sq = (clic_x - cx)**2 + (clic_y - cy)**2
                    if dist_sq < min_sq_dist:
                        min_sq_dist = dist_sq
                        closest_case = case
                
                if closest_case:
                    coup_id = closest_case.get_id()
                    if plateau.jouer_coup(coup_id, self):
                        print(f"-> Coup joué en {closest_case.get_coordonnées()}")
                        return coup_id
                    else:
                        print("Case occupée ou invalide ! Réessayez.")
                else:
                    print("Clic trop éloigné d'une case valide.")
        print(f"Joueur {self.id}, choisissez une case parmi les suivantes :")
        while True:
            try:
                choix = int(input(f"Joueur {self.id}, entrez l'ID de la case où vous voulez jouer : "))
                if choix ==0:
                    #on quitte la partie
                    print("Vous avez quitté la partie.")
                    exit()
                if plateau.jouer_coup(choix, self):
                    break
                else:
                    print("Coup invalide, essayez à nouveau.")
            except ValueError:
                print("Entrée invalide, veuillez entrer un nombre entier.")
        return choix
        
class Yavalath:
    
    def __init__(self):
        self.cases_by_id={}
        self.cases_by_coord={}
        self.make_grid()
        self.sorted_cases_id=sorted(self.cases_by_id.keys())

        # 1. Dictionnaire pour trouver l'index (0-60) à partir de l'ID rapidement
        self.id_to_index = {cases_id: i for i, cases_id in enumerate(self.sorted_cases_id)}
        # 2. Le masque booléen [True, True, True...]
        self.mask_legal = [True] * 61
        
        # On garde votre liste triée pour get_empty_cases()
        self.free_cases_sorted=self.sorted_cases_id.copy()
        self.free_cases_sorted=self.sorted_cases_id.copy()
        self.players=[]
        self.coups=0
        # Variables pour stocker la figure et les axes
        self.fig = None
        self.ax = None


    #numérote un plateau Yavalath hexagonal de côté 5 à l'aide de coordonnées hexagonales (q,r)
    # où q est l'axe haute-gauche à bas-droite et r l'axe haute-droite à bas-gauche
    # on encode les coordonnées en tuples (q,r)
    # on encode q et r sur 3 bits chacun, soit un total de 6 bits par case
    # on applique une conversion de graycode sur les 3 bits de q et la même chose pour r
    # on concatène les deux résultats pour obtenir un entier unique par case
    def make_grid(self):
        coordonnées=[]
        for r in range(-4,5):
            for q in range(-4,5):
                if -r - q >= -4 and -r - q <= 4:
                    coordonnées.append((q,r))


        for q,r in coordonnées:
            q_offset = q + 4
            r_offset = r + 4
            gray_q = graycode(q_offset)
            gray_r = graycode(r_offset)
            code=(gray_q << 4) | gray_r
            case_obj=case(q,r,code)
            self.cases_by_id[code]=case_obj
            self.cases_by_coord[(q,r)]=case_obj

    def afficher_plateau(self):
            if self.fig is None:
                plt.ion()  # Active le mode interactif
                self.fig, self.ax = plt.subplots(figsize=(6,6))
            
            self.ax.clear()  # Efface le contenu précédent

            for code, case_obj in self.cases_by_id.items():
                # conversion hex -> coordonnée x,y pour plot
                q, r = case_obj.get_coordonnées()
                x = q + r/2
                y = r * (3**0.5/2)  # hauteur d'un hexagon parfait
                self.ax.scatter(x, y, s=600, c=case_obj.player.get_color() if case_obj.player else 'lightblue', edgecolors='k')
                self.ax.text(x, y, f"{code:02d}", ha='center', va='center')
            
            self.ax.set_aspect('equal')
            self.ax.axis('off')
            plt.draw()
            plt.pause(0.1)  # Pause pour mettre à jour l'affichage sans bloquer
    
    def get_case_by_id(self, id):
        return self.cases_by_id.get(id, None)
    
    def get_all_cases(self):
        return list(self.cases_by_id)
    
    def reset_plateau(self):
        for case in self.cases_by_id.values():
            case.player = None        
        
        self.mask_legal = [True] * 61
        for player in self.players:
            player.has_lost = False
            player.has_won = False
    def is_full(self):
        return not any(self.mask_legal)
    
    def get_empty_cases(self):
        return [self.cases_by_id[id_val] 
                for id_val, is_free in zip(self.sorted_cases_id, self.mask_legal) 
                if is_free]
        
    def legal_moves(self):
        if self.coups <= 1:
            return [True]*61
        return self.mask_legal[:]
    #si un joureur a aligné 4 pions, il gagne
    def detect_win_loss(self, last_move_id=None):
        directions = [(1,0), (0,1), (-1,1)]

        # Optimisation : on ne vérifie que la case qui vient d'être jouée
        if last_move_id is not None:
            case_start = self.get_case_by_id(last_move_id)
            if not case_start: return # Sécurité
            cases_to_check = [case_start]
        else:
            # Fallback : on scanne tout (utile au chargement ou reset)
            cases_to_check = [c for c in self.cases_by_id.values() if c.is_occupied()]


        for case in cases_to_check:
            if case.is_occupied():
                player = case.player
                for dq, dr in directions:
                    count = 1
                    # vérifier dans une direction
                    q, r = case.get_coordonnées()
                    for step in range(1, 4):
                        next_q = q + dq * step
                        next_r = r + dr * step
                        next_case = self.cases_by_coord.get((next_q, next_r), None)
                        if next_case and next_case.player == player:
                            count += 1
                        else:
                            break
                    # vérifier dans la direction opposée
                    for step in range(1, 4):
                        next_q = q - dq * step
                        next_r = r - dr * step
                        next_case = self.cases_by_coord.get((next_q, next_r), None)
                        if next_case and next_case.player == player:
                            count += 1
                        else:
                            break
                    if count == 3:
                        player.set_lost()
                    if count >= 4:
                        player.set_won()
        return None
    
    def jouer_coup(self, case_id, player):
        case = self.get_case_by_id(case_id)
        if case and not case.is_occupied() or self.coups == 1:
            case.player = player
             # AJOUT DE GESTION DE LISTE
            # Mise à jour du masque booléen en O(1) grâce à l'index
            if case_id in self.id_to_index:
                idx = self.id_to_index[case_id]
                self.mask_legal[idx] = False
            return True
        return False
        
    def new_game(self, players, parties=1, display=True, coups_aleatoires=0):
        self.players = players
        self.display = display
        for player in self.players:
            player.wins = 0
            player.losses = 0
            player.draws = 0
            player.has_lost = False
            player.has_won = False

        try:
            for i in range(parties):
                if self.display:
                    print(f"Début de la partie {i+1}")
                self.reset_plateau()
                self.coups = 0
                if self.display:
                    self.afficher_plateau()
                if coups_aleatoires > 0:
                    cur_player=0
                    for _ in range(min(coups_aleatoires,4)):
                        empty_cases = self.get_empty_cases()
                        if not empty_cases:
                            break
                        random_case = choice(empty_cases)
                        random_player = self.players[cur_player]
                        self.jouer_coup(random_case.get_id(), random_player)
                        self.coups += 1
                        cur_player = (cur_player + 1) % len(self.players)
                    if self.display:
                        print(f"{coups_aleatoires} coups aléatoires joués au début.")
                        self.afficher_plateau()
                self.play_game()
                #input("Appuyez sur Entrée pour continuer...")
                for player in self.players:
                    if self.display:
                        print(f"Joueur {player.get_id()} - Victoires: {player.wins}, Défaites: {player.losses}, Nuls: {player.draws}")
        finally:
            if self.display and self.fig:
                plt.close(self.fig)
                self.fig = None
                self.ax = None

    def play_game(self):
        # boucle principale du jeu
        # chaque joueur joue un coup à tour de rôle
        # on analyse le plateau après chaque coup
        # on affiche le plateau après analyse
        # on termine la partie si un joueur a gagné, s'il ne reste qu'un joueur qui peut jouer ou si le plateau est plein
        while True:
            for player in self.players:
                if not player.has_lost:
                    move_id=player.jouer(self)
                    self.coups += 1
                    self.detect_win_loss(move_id)

                    if self.display:
                        self.afficher_plateau()
                    #vérifie si un joueur a gagné
                    if player.has_won:
                        for p in self.players:
                            if p != player:
                                p.set_lost()
                        if self.display:
                            print(f"Le joueur {player.get_id()} a gagné la partie!")
                        return
                #vérifie s'il ne reste qu'un joueur qui n'a pas perdu
                if len(self.players) - len([p for p in self.players if p.has_lost]) <=1 :
                    for p in self.players:
                        if not p.has_lost:
                            p.set_won()
                            if self.display:
                                print(f"Le joueur {p.get_id()} a gagné la partie!")
                    return
                #vérifie si le plateau est plein
                if self.is_full():
                    for player in self.players:
                        player.draws += 1 if (not player.has_lost and not player.has_won) else 0
                    if self.display:
                        print("Le plateau est plein, la partie se termine par un match nul.")
                    return


class RobotPlayer(player):
    def __init__(self, id, color):
        super().__init__(id, color)
    
    def jouer(self, plateau):
        empty_cases = plateau.get_empty_cases()
        #choisit une case vide au hasard
        choix = choice(empty_cases).get_id() if empty_cases else None
        if plateau.jouer_coup(choix, self):
            return choix
            
        return None
        
        


if __name__ == "__main__":
    plateau=Yavalath()
    players=[RobotPlayer(1, "#b50000"), RobotPlayer(2, "#0000b5"),RobotPlayer(3, "#00b500")]
    plateau.new_game(players,10)

    