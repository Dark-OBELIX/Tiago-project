import os
import random
#from pick_grab import pick_grab
#from verif_jeter import ArmMover as ArmMoverJeter
#from verif_deposer_client import ArmMover as ArmMoverDepositer
#from jeter_homing import ArmMover as ArmMoverJeter_homing
#jeter = ArmMoverJeter()  
#deposer = ArmMoverDepositer()
#jeter_homing = ArmMoverJeter_homing()
stocks = {
    "bleu": 3,
    "jaune": 3,
    "rose": 3,
    "vert": 3
}

choix = input("Choisis un numéro (1, 2, 3 ou 4) : ")

if choix == "1":
    couleur = "bleu"
    print ("navigation vers la zone de pick pour la couleur bleu")
    os.system("python aruco_nav.py 29")
elif choix == "2":
    couleur = "jaune"
    os.system("python aruco_nav.py 30")
elif choix == "3":
    couleur = "rose"
    os.system("python aruco_nav.py 24")
elif choix == "4":
    couleur = "vert"
    os.system("python aruco_nav.py")
else:
    print("Choix invalide")
    exit()

# Vérification du stock avant pick
if stocks[couleur] == 0:
    print(f"Stock épuisé pour {couleur}")
    exit()

# --- Pick ---
if stocks[couleur] == 3:
    os.system("python Tiago-project/navigation/pick_grab.py 3")
elif stocks[couleur] == 2:
    os.system("python Tiago-project/navigation/pick_grab.py 2")
else:
    os.system("python Tiago-project/navigation/pick_grab.py 1")

# --- Simulation vérification couleur ---
bonne_couleur = random.choice([True, False])

if bonne_couleur:
    os.system(f"python verif_deposer_client.py {couleur}")
    print(f"navigation vers la zone de dépôt pour la couleur {couleur}")
    os.system("python jeter_homing.py")
    stocks[couleur] -= 1
    print(f"✅ Bonne couleur prise : {couleur}")
else:
    os.system("python verif_jeter.py")
    print(f"❌ Mauvaise couleur prise (attendu : {couleur})")
    os.system("python jeter_homing.py")

print("Stocks restants :", stocks)
