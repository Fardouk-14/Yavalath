import os
import sys
from Yavalath import Yavalath, human_player
from Model import AI_Player

def jouer_contre_champion():
    # 1. Trouver le modèle
    model_file = "best.pth"
    if not os.path.exists(model_file):
        # Essayer un autre nom si best.pth n'existe pas
        if os.path.exists("champion_final.pth"):
            model_file = "champion_final.pth"
        else:
            print("Erreur : Aucun fichier de modèle trouvé ('best.pth' ou 'champion_final.pth').")
            print("Veuillez d'abord exécuter Model.py pour entraîner une IA.")
            input("Appuyez sur Entrée pour quitter...")
            return

    print(f"--- Chargement du champion : {model_file} ---")
    
    while True:
        print("\n Configuration du match :")
        print("1. Vous commencez (Joueur 1 - Bleu)")
        print("2. L'IA commence (Joueur 1 - Rouge)")
        print("3. Quitter")
        
        try:
            choix = input("Votre choix : ")
            if choix == '3':
                break
            
            plateau = Yavalath()
            
            # Note : Dans Yavalath.py, l'ordre dans la liste définit l'ordre de jeu.
            
            if choix == '1':
                print("\nVous êtes le Joueur 1 (Bleu). Bonne chance !")
                # Vous (1) vs IA (2)
                p1 = human_player(1, "blue")
                p2 = AI_Player(2, "red", model_path=model_file, train_mode=False)
                # Lancement
                plateau.new_game([p1, p2], parties=1, display=True)
                
            elif choix == '2':
                print("\nL'IA est le Joueur 1 (Rouge). Attention, elle est rapide !")
                # IA (1) vs Vous (2)
                p1 = AI_Player(1, "red", model_path=model_file, train_mode=False)
                p2 = human_player(2, "blue")
                # Lancement
                plateau.new_game([p1, p2], parties=1, display=True)
                
            else:
                if choix == '3': break
                print("Choix non reconnu.")
                continue
                
            print("\nPartie terminée.")
            replay = input("Voulez-vous rejouer ? (o/n) : ")
            if replay.lower() != 'o':
                break
                
        except KeyboardInterrupt:
            print("\nInterruption.")
            break
        except Exception as e:
            print(f"Une erreur est survenue : {e}")
            break

if __name__ == "__main__":
    jouer_contre_champion()