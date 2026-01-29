#!/usr/bin/env python3
import rospy

rospy.init_node("check_color_node")

rospy.loginfo("Recherche de la couleur sur le serveur ROS...")

# On boucle tant que le paramètre n'existe pas ou vaut "aucune"
couleur = "aucune"
while not rospy.is_shutdown() and couleur == "aucune":
    # On regarde dans la "boîte aux lettres" ROS
    couleur = rospy.get_param('/brochure_color', "aucune")
    
    if couleur == "aucune":
        rospy.loginfo("En attente de la détection de couleur...")
        rospy.sleep(1.0) # On attend 1 seconde avant de revérifier

print(f"✅ Succès ! La couleur récupérée est : {couleur}")

# --- La suite de ton code Tiago ici ---
if couleur == "jaune":
    # robot.move_to(...)
    pass