#!/usr/bin/env python3
import rospy

rospy.init_node("check_color_node")

# On récupère la valeur stockée sur le serveur ROS
# Le deuxième argument "inconnu" est la valeur par défaut si rien n'est trouvé
couleur = rospy.get_param('/couleur_brochure_detectee', "aucune")

print(f"La couleur stockée dans ROS est : {couleur}")
