#!/usr/bin/env python3
import rospy
import numpy as np
import tf
from sensor_msgs.msg import PointCloud2
import sensor_msgs.point_cloud2 as pc2
from moveit_commander import PlanningSceneInterface
from geometry_msgs.msg import PoseStamped

class TablePlaneDetector:
    def __init__(self):
        rospy.init_node("table_plane_detector")

        self.scene = PlanningSceneInterface()
        self.tf = tf.TransformListener()

        rospy.sleep(2)
        # Supprime les objets précédents
        self.scene.remove_world_object()

        # Subscriber du point cloud de la caméra
        rospy.Subscriber(
            "/xtion/depth/points",
            PointCloud2,
            self.cloud_cb,
            queue_size=1
        )

        rospy.loginfo("⏳ Waiting for table plane...")
        rospy.spin()

    def cloud_cb(self, cloud):
        points = []

        # Lire tous les points valides
        for p in pc2.read_points(cloud, field_names=("x", "y", "z"), skip_nans=True):
            points.append([p[0], p[1], p[2]])

        if len(points) < 500:
            return

        pts = np.array(points)

        # Filtrer selon la hauteur de la table (0.5-1.0 m)
        pts = pts[(pts[:, 2] > 0.5) & (pts[:, 2] < 1.0)]
        if len(pts) < 200:
            return

        # Calcul approximatif du plateau de la table
        table_top_z = np.median(pts[:, 2])

        xmin, xmax = np.min(pts[:, 0]), np.max(pts[:, 0])
        ymin, ymax = np.min(pts[:, 1]), np.max(pts[:, 1])
        size_x = xmax - xmin
        size_y = ymax - ymin

        # 🔹 Hauteur de la box réduite pour ne pas bloquer le bras
        size_z = 0.05  # 5 cm d'épaisseur
        pose_z = table_top_z - size_z / 2  # centre de la box

        # Définir la pose
        pose = PoseStamped()
        pose.header.frame_id = cloud.header.frame_id
        pose.pose.position.x = (xmin + xmax) / 2
        pose.pose.position.y = (ymin + ymax) / 2
        pose.pose.position.z = pose_z
        pose.pose.orientation.w = 1.0  # pas de rotation

        # Ajouter la box dans MoveIt!
        self.scene.add_box("table", pose, (size_x, size_y, size_z))
        rospy.loginfo(f"✅ Table collision box added at z={pose_z:.2f} m, size_z={size_z:.2f} m")

        # Sleep rapide pour que MoveIt! reçoive bien la box
        rospy.sleep(1)

        # Terminer le node
        rospy.signal_shutdown("Table box added")

if __name__ == "__main__":
    TablePlaneDetector()
