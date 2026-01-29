import os
import random
from pick_grab import pick_grab
from verif_jeter import ArmMover as ArmMoverJeter
from verif_deposer_client import ArmMover as ArmMoverDepositer
from jeter_homing import ArmMover as ArmMoverJeter_homing
jeter = ArmMoverJeter()  
deposer = ArmMoverDepositer()
jeter_homing = ArmMoverJeter_homing()
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
pick = pick_grab()
pick.main(stocks[couleur])

# --- Simulation vérification couleur ---
bonne_couleur = random.choice([True, False])

if bonne_couleur:
    print(f"navigation vers la zone de dépôt pour la couleur {couleur}")
    deposer.move_arm()
    jeter_homing.move_arm()
    stocks[couleur] -= 1
    print(f"✅ Bonne couleur prise : {couleur}")
else:
    jeter.move_arm()
    jeter_homing.move_arm()
    print(f"❌ Mauvaise couleur prise (attendu : {couleur})")

print("Stocks restants :", stocks)
