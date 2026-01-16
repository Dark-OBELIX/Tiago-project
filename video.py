#!/usr/bin/env python3
import rospy   
import cv2 
from sensor_msgs.msg import Image   
from cv_bridge import CvBridge    

# Instance CvBridge utilisée pour convertir les messages ROS en images OpenCV
bridge = CvBridge()

def image_cb(msg):
    """
    Callback appelé à chaque nouvelle image reçue sur le topic ROS.
    """
    try:
        # Conversion du message ROS (sensor_msgs/Image)
        frame = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

        # Affiche l’image dans une fenêtre OpenCV
        cv2.imshow("Camera", frame)

        # Permet à OpenCV de rafraîchir la fenêtre
        cv2.waitKey(1)

    except Exception as e:
        # Affiche l’erreur dans les logs ROS si la conversion ou l’affichage échoue
        print('agougggaa')
        rospy.logerr(e)

def main():
    """
    Fonction principale du node ROS.
    """
    # Initialisation du node ROS
    rospy.init_node("camera_viewer")
    # Abonnement au topic image de la caméra RGB
    rospy.Subscriber(
        "/xtion/rgb/image_raw",  # Topic image publié par la caméra
        Image,                   # Type de message attendu
        image_cb,                # Callback appelée à chaque image
        queue_size=1             # On garde seulement la dernière image
    )

    # Boucle ROS pour garder le node actif 
    rospy.spin()

if __name__ == "__main__":
    # Point d’entrée du script
    main()
