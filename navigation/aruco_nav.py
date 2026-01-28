#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import cv2
import cv2.aruco as aruco
import numpy as np
import os
import sys
import actionlib
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import tf.transformations as tf_trans
import tf2_ros

class ArucoDocker:
    def __init__(self):
        rospy.init_node('tiago_aruco_docking', anonymous=True)

        # --- RECUPERATION ARGUMENT ID ---
        # On regarde si un ID est passé en argument (ex: rosrun ... aruco_nav.py 42)
        if len(sys.argv) > 1:
            try:
                self.target_id = int(sys.argv[1])
                rospy.loginfo(f"TARGET ARUCO ID: {self.target_id}")
            except ValueError:
                rospy.logwarn("Argument invalide. ID par defaut: 0")
                self.target_id = 0
        else:
            self.target_id = 0 # Valeur par defaut
            rospy.loginfo(f"Aucun ID specifie. Defaut: {self.target_id}")

        # --- REGLAGES UTILISATEUR ---
        self.marker_size = 0.164
        self.target_dist = 0.44   # Distance finale souhaitée
        self.approach_dist = 0.90 # Distance de fin move_base / début servoing
        
        # CORRECTION DU DECALAGE "TROP A DROITE"
        # Si le robot finit trop à droite, c'est que la caméra n'est pas centrée
        # ou que l'optique a un biais.
        # Valeur positive = décale le robot vers la GAUCHE
        # Valeur négative = décale le robot vers la DROITE
        self.lateral_bias = 0.00 # Essayez 0.02 (2cm) ou -0.02 selon le sens

        # Gains du controleur PID (A ajuster si le robot oscille)
        self.kp_v = 0.2  # Gain vitesse linéaire (Avancer/Reculer)
        self.kp_w = 0.4  # Gain vitesse angulaire (Tourner)
        self.max_linear_speed = 0.15 # Vitesse max lente pour la précision

        # --- SETUP ---
        self.camera_topic = "/xtion/rgb/image_raw"
        self.cmd_vel_topic = "/mobile_base_controller/cmd_vel" # Verifiez ce topic sur Tiago++
        
        self.state = "SEARCHING" # Start in SEARCHING mode
        
        # Variables pour la recherche (Sweep)
        self.search_start_yaw = None
        self.search_dir = "LEFT" # Ou RIGHT
        self.search_limit = 1.5 # ~90 degres (scan 180 total)
        
        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        self.aruco_params = aruco.DetectorParameters_create()
        self.bridge = CvBridge()
        
        # Publishers / Subscribers
        self.vel_pub = rospy.Publisher(self.cmd_vel_topic, Twist, queue_size=1)
        self.image_sub = rospy.Subscriber(self.camera_topic, Image, self.image_callback)
        
        # Move Base
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.loginfo("Connexion move_base...")
        # self.client.wait_for_server() # Decommenter sur le vrai robot
        rospy.loginfo("Systeme pret. Montrez un ArUco.")

        # Calibration
        try:
            cwd = os.getcwd()
            self.mtx = np.load(os.path.join(cwd, "calibration_matrix.npy"))
            self.dist_coeff = np.load(os.path.join(cwd, "dist_coeffs.npy"))
        except:
            self.mtx = np.array([[520, 0, 320], [0, 520, 240], [0, 0, 1]], dtype=float)
            self.dist_coeff = np.zeros((5, 1))

        # TF Buffer
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

    def get_transform(self, target, source):
        try:
            return self.tf_buffer.lookup_transform(target, source, rospy.Time(0), rospy.Duration(1.0))
        except:
            return None

    def get_yaw(self, q):
        # Helper pour extraire le yaw d'un quaternion
        euler = tf_trans.euler_from_quaternion([q.x, q.y, q.z, q.w])
        return euler[2]
    
    def normalize_angle(self, angle):
        # Normalise entre -pi et pi
        while angle > np.pi: angle -= 2.0 * np.pi
        while angle < -np.pi: angle += 2.0 * np.pi
        return angle

    def image_callback(self, data):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError:
            return

        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = aruco.detectMarkers(gray, self.aruco_dict, parameters=self.aruco_params)
        
        target_detected = False
        target_index = -1
        
        # Filtrer pour trouver NOTRE id
        if ids is not None and len(ids) > 0:
            ids_flat = ids.flatten()
            if self.target_id in ids_flat:
                target_index = np.where(ids_flat == self.target_id)[0][0]
                target_detected = True
        
        if target_detected:
            # Pose Marker Cible
            rvec, tvec, _ = aruco.estimatePoseSingleMarkers(corners, self.marker_size, self.mtx, self.dist_coeff)
            
            # On selectionne celui qui correspond a target_index
            rvec_target = rvec[target_index]
            tvec_target = tvec[target_index]
            
            x_cam = tvec_target[0][0]
            z_cam = tvec_target[0][2]

            # Dessin Debug
            aruco.drawAxis(cv_image, self.mtx, self.dist_coeff, rvec_target, tvec_target, 0.05)
            cv2.putText(cv_image, f"TARGET {self.target_id} FOUND: {z_cam:.2f}m", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # --- LOGIQUE ETATS ---
            if self.state == "SEARCHING":
                rospy.loginfo(f"ArUco {self.target_id} trouve ! Arret recherche.")
                self.vel_pub.publish(Twist()) # Stop rotation
                
                tf_map_cam = self.get_transform("map", "xtion_rgb_optical_frame")
                if tf_map_cam:
                    self.start_coarse_approach(rvec_target, tvec_target, tf_map_cam)

            elif self.state == "VISUAL_SERVOING":
                self.process_visual_servoing(x_cam, z_cam)

        else:
            # Aucun marker ou pas le bon marker
            if self.state == "SEARCHING":
                self.perform_search_scan()
            
            elif self.state == "VISUAL_SERVOING":
                self.stop_robot()
        
        # Affichage
        cv2.imshow("Docking View", cv_image)
        cv2.waitKey(3)

    def perform_search_scan(self):
        # Comportement de recherche: Scan 180 degres devant
        
        # 1. Initialisation de la reference de depart
        if self.search_start_yaw is None:
            tf_base = self.get_transform("odom", "base_footprint")
            if tf_base:
                self.search_start_yaw = self.get_yaw(tf_base.transform.rotation)
            return # On attend d'avoir la ref

        # 2. Lecture position actuelle
        tf_base = self.get_transform("odom", "base_footprint")
        if not tf_base:
            return 
        
        current_yaw = self.get_yaw(tf_base.transform.rotation)
        diff = self.normalize_angle(current_yaw - self.search_start_yaw)
        
        cmd = Twist()
        cmd.linear.x = 0.0
        
        # 3. Scan Gauche / Droite
        if self.search_dir == "LEFT":
            if diff < self.search_limit: # Tant qu'on a pas atteint +90 deg
                cmd.angular.z = 0.4
            else:
                self.search_dir = "RIGHT" # On inverse
        
        elif self.search_dir == "RIGHT":
            if diff > -self.search_limit: # Tant qu'on a pas atteint -90 deg
                cmd.angular.z = -0.4 
            else:
                self.search_dir = "LEFT" # On inverse
        
        self.vel_pub.publish(cmd)

    def start_coarse_approach(self, rvec, tvec, trans_map_cam):
        # Meme calcul que precedemment pour aller a self.approach_dist (0.9m)
        rot_matrix_marker, _ = cv2.Rodrigues(rvec)
        t_mat_marker = np.eye(4)
        t_mat_marker[:3, :3] = rot_matrix_marker
        t_mat_marker[:3, 3] = tvec.flatten()

        q = trans_map_cam.transform.rotation
        rot_matrix_cam = tf_trans.quaternion_matrix([q.x, q.y, q.z, q.w])
        t = trans_map_cam.transform.translation
        t_mat_cam = np.eye(4)
        t_mat_cam[:3, :3] = rot_matrix_cam[:3, :3]
        t_mat_cam[:3, 3] = [t.x, t.y, t.z]

        mat_map_marker = np.dot(t_mat_cam, t_mat_marker)
        
        # Vecteur normal Z
        z_axis = mat_map_marker[:3, 2]
        pos_marker = mat_map_marker[:3, 3]
        
        # Point cible (Approche lointaine)
        target_x = pos_marker[0] + (z_axis[0] * self.approach_dist)
        target_y = pos_marker[1] + (z_axis[1] * self.approach_dist)
        
        # Orientation vers le marker
        yaw = np.arctan2(pos_marker[1] - target_y, pos_marker[0] - target_x)
        q_robot = tf_trans.quaternion_from_euler(0, 0, yaw)

        # Envoi Goal Move Base
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = target_x
        goal.target_pose.pose.position.y = target_y
        goal.target_pose.pose.orientation.x = q_robot[0]
        goal.target_pose.pose.orientation.y = q_robot[1]
        goal.target_pose.pose.orientation.z = q_robot[2]
        goal.target_pose.pose.orientation.w = q_robot[3]

        self.state = "NAV_APPROACH"
        self.client.send_goal(goal, done_cb=self.done_cb)

    def done_cb(self, status, result):
        if status == 3: # SUCCEEDED
            rospy.loginfo("MoveBase fini. Passage en mode SERVOING VISUEL.")
            rospy.sleep(0.5)
            self.state = "VISUAL_SERVOING"
        else:
            rospy.logwarn("Echec MoveBase. Reset.")
            self.state = "IDLE"

    def process_visual_servoing(self, x_cam, z_cam):
        cmd = Twist()

        # 1. Erreur de Distance (Z)
        # On veut aller jusqu'a self.target_dist (0.5m)
        error_distance = z_cam - self.target_dist

        # 2. Erreur Laterale (X)
        # On veut que x_cam soit 0 (centré). 
        # C'est ici qu'on applique le biais manuel "trop a droite"
        # Si le robot est trop a droite, x_cam est positif (ou negatif selon repere).
        # On ajoute le biais artificiel.
        target_x = 0.0 + self.lateral_bias 
        error_lateral = -1 * (x_cam - target_x) # Inversion souvent necessaire selon camera

        # --- CONDITION D'ARRET ---
        # Si on est a moins de 1cm de la cible en distance
        if abs(error_distance) < 0.01:
            rospy.loginfo("Position atteinte ! Arret.")
            self.stop_robot()
            self.state = "DONE"
            return

        # --- LOI DE COMMANDE (P-CONTROLLER) ---
        
        # Vitesse Lineaire : proportionnelle a la distance restante
        linear_x = self.kp_v * error_distance
        # Saturation vitesse
        cmd.linear.x = max(min(linear_x, self.max_linear_speed), -self.max_linear_speed)

        # Vitesse Angulaire : proportionnelle a l'erreur laterale
        # Le Tiago tourne pour centrer l'image
        angular_z = self.kp_w * error_lateral
        cmd.angular.z = max(min(angular_z, 0.5), -0.5)

        # Securité: Si on est trop pres, on recule doucement ou on stop
        if z_cam < (self.target_dist - 0.05):
            cmd.linear.x = -0.05 # Recul lent de sécurité

        self.vel_pub.publish(cmd)

    def stop_robot(self):
        self.vel_pub.publish(Twist()) # Twist vide = arret

if __name__ == '__main__':
    try:
        node = ArucoDocker()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
    finally:
        cv2.destroyAllWindows()
