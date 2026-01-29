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
        self.scene.remove_world_object()

        rospy.Subscriber(
            "/xtion/depth/points",
            PointCloud2,
            self.cloud_cb,
            queue_size=1
        )

        rospy.loginfo("Waiting for table plane...")
        rospy.spin()

    def cloud_cb(self, cloud):
        points = []

        for p in pc2.read_points(
            cloud,
            field_names=("x", "y", "z"),
            skip_nans=True
        ):
            points.append([p[0], p[1], p[2]])

        if len(points) < 500:
            return

        pts = np.array(points)

        # 🔹 filtrage hauteur (table ≈ 0.6–0.9 m)
        pts = pts[(pts[:, 2] > 0.5) & (pts[:, 2] < 1.0)]
        if len(pts) < 200:
            return

        # 🔹 calcul "plan" simple (médiane)
        table_top_z = np.median(pts[:, 2])
        floor_z = 0.0

        xmin, xmax = np.min(pts[:, 0]), np.max(pts[:, 0])
        ymin, ymax = np.min(pts[:, 1]), np.max(pts[:, 1])
        size_x = xmax - xmin
        size_y = ymax - ymin
        size_z = table_top_z - floor_z

        pose = PoseStamped()
        pose.header.frame_id = cloud.header.frame_id
        pose.pose.position.x = (xmin + xmax) / 2
        pose.pose.position.y = (ymin + ymax) / 2
        pose.pose.position.z = size_z / 2   # milieu du cube du sol au plateau
        pose.pose.orientation.w = 1.0

        self.scene.add_box("table", pose, (size_x, size_y, size_z))
        rospy.loginfo("Table collision box added")

        rospy.signal_shutdown("done")

if __name__ == "__main__":
    TablePlaneDetector()
