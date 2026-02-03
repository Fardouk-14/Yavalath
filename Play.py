import os
import sys
from Yavalath import Yavalath, human_player
from Model import AI_Player
from SmartPlayer import SmartPlayer

def jouer_contre_champion():
    # 1. Trouver le modèle
    model_file = "AI/best.pth"
    if not os.path.exists(model_file):
        # Essayer un autre nom si best.pth n'existe pas
        if os.path.exists("AI/champion_final.pth"):
            model_file = "AI/champion_final.pth"
        else:
            print("Attention : Aucun fichier de modèle trouvé ('best.pth' ou 'champion_final.pth').")
            model_file = None

    if model_file:
        print(f"--- Modèle NN disponible : {model_file} ---")
    
    while True:
        print("\n=== YAVALATH - Menu ===")
        print("1. Jouer contre l'IA (Réseau de neurones) - Vous commencez")
        print("2. Jouer contre l'IA (Réseau de neurones) - L'IA commence")
        print("3. Jouer contre le Bot heuristique - Vous commencez")
        print("4. Jouer contre le Bot heuristique - Le Bot commence")
        print("5. IA (NN) vs Bot heuristique (démonstration)")
        print("6. Quitter")
        
        try:
            choix = input("Votre choix : ")
            
            if choix == '6':
                break
            
            plateau = Yavalath()
            
            if choix == '1':
                if not model_file:
                    print("Pas de modèle NN disponible. Entraînez d'abord avec Model.py")
                    continue
                print("\nVous êtes Bleu, l'IA (NN) est Rouge. Bonne chance !")
                p1 = human_player(1, "blue")
                p2 = AI_Player(player_id=2, color="red", model_path=model_file)
                plateau.new_game([p1, p2], parties=1, display=True)
                
            elif choix == '2':
                if not model_file:
                    print("Pas de modèle NN disponible. Entraînez d'abord avec Model.py")
                    continue
                print("\nL'IA (NN) est Rouge, vous êtes Bleu.")
                p1 = AI_Player(player_id=1, color="red", model_path=model_file)
                p2 = human_player(2, "blue")
                plateau.new_game([p1, p2], parties=1, display=True)
                
            elif choix == '3':
                print("\nVous êtes Bleu, le Bot est Vert.")
                p1 = human_player(1, "blue")
                p2 = SmartPlayer(2, "#00b500")
                plateau.new_game([p1, p2], parties=1, display=True)
                
            elif choix == '4':
                print("\nLe Bot est Vert, vous êtes Bleu.")
                p1 = SmartPlayer(1, "#00b500")
                p2 = human_player(2, "blue")
                plateau.new_game([p1, p2], parties=1, display=True)
                
            elif choix == '5':
                if not model_file:
                    print("Pas de modèle NN disponible. Entraînez d'abord avec Model.py")
                    continue
                print("\nDémonstration : IA (NN) Rouge vs Bot Vert")
                p1 = AI_Player(player_id=1, color="red", model_path=model_file)
                p2 = SmartPlayer(2, "#00b500")
                plateau.new_game([p1, p2], parties=3, display=True)
                
            else:
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
            import traceback
            traceback.print_exc()
            break

if __name__ == "__main__":
    jouer_contre_champion()