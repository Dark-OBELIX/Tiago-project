#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import cv2
import cv2.aruco as aruco
import numpy as np
import tf
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CameraInfo
from moveit_commander import PlanningSceneInterface
from geometry_msgs.msg import PoseStamped
from visualization_msgs.msg import Marker

class TableObstacleDetector:
    def __init__(self):
        rospy.init_node("table_obstacle_detector")

        # --- PARAMÈTRES RÉELS ---
        self.target_ids = [24, 26, 29, 30] 
        self.marker_length = 0.164  # 16.4cm

        # Dimensions de la table
        self.table_width = 0.70   
        self.table_depth = 0.50   
        self.table_height = 0.76  

        # --- AJUSTEMENT DE L'OFFSET (Correction du vol) ---
        # Si la table vole de 5cm, mets -0.05. Si elle s'enfonce, mets +0.05.
        self.offset_z = -0.05 
        # --------------------------------------------------

        self.bridge = CvBridge()
        self.scene = PlanningSceneInterface()
        self.tf_listener = tf.TransformListener()
        
        rospy.loginfo("🧹 Nettoyage de la scène MoveIt...")
        self.clean_scene()
        
        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_1000)
        self.aruco_params = aruco.DetectorParameters_create()

        self.camera_matrix = None
        self.dist_coeffs = None
        self.box_added = False

        self.marker_pub = rospy.Publisher('/detected_table_marker', Marker, queue_size=10)
        
        rospy.loginfo("⏳ En attente de calibration et d'images...")
        self.cam_info_sub = rospy.Subscriber("/xtion/rgb/camera_info", CameraInfo, self.camera_info_callback)
        self.image_sub = rospy.Subscriber("/xtion/rgb/image_rect_color", Image, self.image_callback)

        rospy.spin()

    def clean_scene(self):
        rospy.sleep(1.0) 
        for name in self.scene.get_known_object_names():
            self.scene.remove_world_object(name)
        rospy.loginfo("✨ Scène nettoyée.")

    def camera_info_callback(self, msg):
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.K).reshape((3, 3))
            self.dist_coeffs = np.array(msg.D)
            rospy.loginfo("✅ Calibration caméra chargée.")

    def image_callback(self, msg):
        if self.camera_matrix is None or self.box_added:
            return

        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception: return

        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = aruco.detectMarkers(gray, self.aruco_dict, parameters=self.aruco_params)

        if ids is not None:
            ids_flat = ids.flatten()
            rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(corners, self.marker_length, self.camera_matrix, self.dist_coeffs)

            for i, marker_id in enumerate(ids_flat):
                if marker_id in self.target_ids:
                    p = PoseStamped()
                    p.header.frame_id = msg.header.frame_id
                    p.header.stamp = rospy.Time(0)
                    p.pose.position.x = tvecs[i][0][0]
                    p.pose.position.y = tvecs[i][0][1]
                    p.pose.position.z = tvecs[i][0][2]
                    p.pose.orientation.w = 1.0

                    try:
                        self.tf_listener.waitForTransform("base_link", p.header.frame_id, rospy.Time(0), rospy.Duration(1.0))
                        pose_base = self.tf_listener.transformPose("base_link", p)
                        
                        self.create_accurate_table(pose_base)
                        self.box_added = True
                        
                        rospy.loginfo("🚀 Table ajoutée. Fermeture...")
                        rospy.signal_shutdown("Succès")
                        break
                    except Exception as e:
                        rospy.logwarn(f"TF Error: {e}")

    def create_accurate_table(self, marker_pose):
        mx = marker_pose.pose.position.x
        my = marker_pose.pose.position.y

        size_x = self.table_width
        size_y = self.table_depth
        size_z = self.table_height 

        table_pose = PoseStamped()
        table_pose.header.frame_id = "base_link"
        table_pose.pose.position.x = mx 
        table_pose.pose.position.y = my
        
        # Application de l'OFFSET pour corriger le "vol"
        # On calcule le centre (Z/2) et on ajoute l'offset
        table_pose.pose.position.z = (self.table_height / 2.0) + self.offset_z
        
        table_pose.pose.orientation.w = 1.0

        self.scene.add_box("real_table_obstacle", table_pose, (size_x, size_y, size_z))
        self.publish_debug_marker(table_pose, size_x, size_y, size_z)
        rospy.sleep(0.5) 
        
        rospy.loginfo(f"✅ TABLE CRÉÉE : x={mx:.2f}, y={my:.2f}, Z-centre={table_pose.pose.position.z:.2f}")

    def publish_debug_marker(self, pose, sx, sy, sz):
        m = Marker()
        m.header.frame_id = "base_link"
        m.header.stamp = rospy.Time.now()
        m.ns = "table_real"
        m.id = 0
        m.type = Marker.CUBE
        m.action = Marker.ADD
        m.pose = pose.pose
        m.scale.x = sx
        m.scale.y = sy
        m.scale.z = sz
        m.color.r = 1.0; m.color.g = 0.5; m.color.b = 0.0; m.color.a = 0.6 
        self.marker_pub.publish(m)

if __name__ == "__main__":
    TableObstacleDetector()