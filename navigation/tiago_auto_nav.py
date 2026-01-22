#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import rospy
import cv2
import cv2.aruco as aruco
import numpy as np
import tf2_ros
import math
import actionlib
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, JointState
from cv_bridge import CvBridge
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint # Pour la tete

class TiagoDockingMaster:
    def __init__(self):
        rospy.init_node("tiago_docking_master", anonymous=False)
        
        # --- CONFIGURATION ---
        self.marker_size = 0.164
        self.approach_dist_mb = 1.20  # Phase 1: MoveBase s'arrete la
        self.switch_blind_dist = 0.60 # Phase 3: On passe en aveugle ici (60cm)
        self.final_target_dist = 0.50 # On veut finir ici
        
        # --- INIT ---
        self.bridge = CvBridge()
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        
        # MoveBase Client
        self.mb_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        # self.mb_client.wait_for_server() # Décommenter sur le vrai robot

        # Variables d'état
        self.live_data = {"detected": False, "dist": 0.0, "lateral": 0.0, "yaw": 0.0}
        self.current_pose = {"x": 0, "y": 0, "theta": 0}

        # Publishers / Subscribers
        self.cmd_pub = rospy.Publisher("/mobile_base_controller/cmd_vel", Twist, queue_size=1)
        self.head_pub = rospy.Publisher("/head_controller/command", JointTrajectory, queue_size=1)
        
        self.sub_img = rospy.Subscriber("/xtion/rgb/image_raw", Image, self.image_cb)
        self.sub_odom = rospy.Subscriber("/mobile_base_controller/odom", Odometry, self.odom_cb)
        
        
        # Calibration (Simulée ou chargée)
        try:
            # Remplace par tes chargements .npy ici
            self.mtx = np.array([[520, 0, 320], [0, 520, 240], [0, 0, 1]], dtype=float) 
            self.dist_coeff = np.zeros((5, 1))
        except: pass

        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        self.params = aruco.DetectorParameters_create()

    def odom_cb(self, msg):
        self.current_pose["x"] = msg.pose.pose.position.x
        self.current_pose["y"] = msg.pose.pose.position.y
        # Conversion quaternion simple
        q = msg.pose.pose.orientation
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        self.current_pose["theta"] = math.atan2(siny_cosp, cosy_cosp)

    def image_cb(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = aruco.detectMarkers(gray, self.aruco_dict, parameters=self.params)

            if ids is not None:
                rvec, tvec, _ = aruco.estimatePoseSingleMarkers(corners[0], self.marker_size, self.mtx, self.dist_coeff)
                
                # Z est la distance face camera
                dist = tvec[0][0][2]
                # X est le decalage lateral (gauche/droite camera)
                lateral = tvec[0][0][0]
                
                # HUD Debug
                cv2.drawFrameAxes(frame, self.mtx, self.dist_coeff, rvec[0], tvec[0], 0.1)
                cv2.putText(frame, f"DIST: {dist:.2f}m", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                
                self.live_data = {"detected": True, "dist": dist, "lateral": lateral}
            else:
                self.live_data["detected"] = False

            cv2.imshow("Tiago Eye", frame)
            cv2.waitKey(1)
        except Exception: pass

    # --- ACTION 1 : MOUVEMENT DE TeTE ---
    def tilt_head_down(self):
        """ Baisse la tete pour voir les pieds de table """
        print("entree dans la fonciton tilt head down")
        traj = JointTrajectory()
        traj.joint_names = ["head_1_joint", "head_2_joint"]
        p = JointTrajectoryPoint()
        p.positions = [0.0, -0.2] # -0.6 rad (regarde vers le bas)
        p.time_from_start = rospy.Duration(1.0)
        
        traj.points = [p]
        self.head_pub.publish(traj)
        print("fin tilt")
        rospy.sleep(1.0)

    # --- ACTION 2 : CONTROL LOOP VISUEL (SMOOTH) ---
    def visual_servoing_approach(self):
        print(">>> DEBUT DU VISUAL SERVOING")
        r = rospy.Rate(10)
        
        # On force la tete en bas avant de commencer l'approche fine
        self.tilt_head_down()

        while not rospy.is_shutdown():
            data = self.live_data
            
            # CONDITION DE SORTIE : Si on est assez pres, on passe en aveugle
            # Ou si on a perdu le marqueur alors qu'on etait deje pres (< 1m)
            if (data["detected"] and data["dist"] < self.switch_blind_dist):
                print(f">>> Zone aveugle atteinte ({data['dist']:.2f}m). Stop Visuel.")
                break
            
            # Si perdu loin, on attend un peu (ou on tourne pour chercher)
            if not data["detected"]:
                self.cmd_pub.publish(Twist()) # Stop securite
                continue

            # LOI DE COMMANDE (P-Controller)
            cmd = Twist()
            
            # 1. Vitesse d'avance (ralentit en approchant)
            err_dist = data["dist"] - self.switch_blind_dist
            cmd.linear.x = max(0.05, min(0.2, err_dist * 0.5))
            
            # 2. Correction Lateale (tourner pour corriger X)
            # Sur Tiago : Y camera = gauche/droite robot ? Verifier le frame.
            # Souvent: -X image correspond a Y robot. A tester.
            # Ici on fait un PID simple sur l'erreur laterale
            cmd.angular.z = -1.5 * data["lateral"]  # Gain 1.5 a ajuster
            
            # Saturation
            cmd.angular.z = max(-0.4, min(0.4, cmd.angular.z))
            
            self.cmd_pub.publish(cmd)
            r.sleep()
            
        self.cmd_pub.publish(Twist()) # Stop fin de phase

    # --- ACTION 3 : APPROCHE AVEUGLE (ODOMETRIE) ---
    def blind_finish(self):
        print(">>> FINAL APPROACH (BLIND ODOMETRY)")
        
        # On enregistre la position de depart de la phase aveugle
        start_x = self.current_pose["x"]
        start_y = self.current_pose["y"]
        
        target_travel = self.switch_blind_dist - self.final_target_dist
        print(f"Objectif : Avancer de {target_travel:.3f}m tout droit")
        
        r = rospy.Rate(20)
        while not rospy.is_shutdown():
            # Distance euclidienne parcourue depuis le switch
            dx = self.current_pose["x"] - start_x
            dy = self.current_pose["y"] - start_y
            dist_done = math.sqrt(dx*dx + dy*dy)
            
            remaining = target_travel - dist_done
            
            if remaining <= 0.005: # 5mm tolerance
                break
            
            cmd = Twist()
            cmd.linear.x = 0.1 # Vitesse lente constante
            # Pas de rotation, on suppose qu'on est aligne
            self.cmd_pub.publish(cmd)
            r.sleep()
            
        self.cmd_pub.publish(Twist()) # ARRET FINAL
        print(">>> DOCKING TERMINE.")

    def run(self):
        # Phase 1 : MoveBase (Tu peux remettre ton code ici)
        # self.trigger_movebase(...) 
        print("1. Phase MoveBase (Simulee passee)")
        
        # Phase 2 : Approche Visuelle avec correction continue
        self.visual_servoing_approach()

        # SECURITE : Si on a fait Ctrl+C pendant la phase 2, on arrete tout ici
        if rospy.is_shutdown():
            print(">>> Arret d'urgence detecte. Pas de phase finale.")
            return
        
        # Phase 3 : Finition Odometrique
        self.blind_finish()

if __name__ == '__main__':
    try:
        node = TiagoDockingMaster()
        rospy.sleep(1) # Wait for pubs
        node.run()
    except rospy.ROSInterruptException: pass
