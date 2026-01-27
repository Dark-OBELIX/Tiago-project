import rospy
from geometry_msgs.msg import Twist
import Aruco  # Module de détection ArUco


# --- CONFIGURATION ---
TARGET_ID = 26  # ID ArUco à détecter
# --------------------


def rotate_and_search(pub, reader, speed, duration, target_id):
    """
    Fait tourner le robot et s'arrête immédiatement si l'ID cible est détecté.
    Retourne True si l'ID est trouvé, False sinon.
    """
    cmd = Twist()
    cmd.angular.z = speed

    rate = rospy.Rate(20)  # Fréquence de vérification (Hz)
    start_time = rospy.Time.now()

    rospy.loginfo(f"Recherche de l'ID {target_id} en cours...")

    while (rospy.Time.now() - start_time).to_sec() < duration:
        # Vérification de la détection de l'ID cible
        if reader.is_id_detected(target_id):
            rospy.logwarn(f"ID {target_id} détecté. Arrêt du robot.")
            pub.publish(Twist())  # Arrêt immédiat
            return True

        # Rotation continue
        pub.publish(cmd)
        rate.sleep()

    # Fin du mouvement si l'ID n'a pas été trouvé
    pub.publish(Twist())
    rospy.loginfo("Recherche terminée sans détection.")

    return False


def main():
    rospy.init_node("aruco_search_node")

    # Initialisation des composants
    reader = Aruco.ArUcoReader()
    cmd_pub = rospy.Publisher(
        "/mobile_base_controller/cmd_vel",
        Twist,
        queue_size=1
    )

    # Temps de stabilisation au démarrage
    rospy.sleep(1.0)

    # Étape 1 : rotation à gauche
    found = rotate_and_search(
        cmd_pub,
        reader,
        speed=0.3,
        duration=6.0,
        target_id=TARGET_ID
    )

    # Étape 2 : rotation à droite si non trouvé
    if not found:
        rospy.loginfo("ID non détecté à gauche, rotation à droite.")
        found = rotate_and_search(
            cmd_pub,
            reader,
            speed=-0.3,
            duration=12.0,
            target_id=TARGET_ID
        )

    # Résultat final
    if found:
        rospy.loginfo(f"Mission réussie : ID {TARGET_ID} détecté.")
    else:
        rospy.loginfo(
            f"ID {TARGET_ID} non détecté. IDs vus : {reader.get_all_ids()}"
        )


if __name__ == "__main__":
    main()
