#!/usr/bin/env python3
import rospy
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
""" import sys
import argparse
parser = argparse.ArgumentParser(description="Contrôle des pinces du robot TiaGo")
parser.add_argument("gripper", choices=["left", "right"], help="Sélectionner la pince à bouger")
parser.add_argument("position", type=int, choices=[1, 2], help="Position prédéfinie : 1 (ouvert), 2 (fermé)")
args = parser.parse_args() """

def move_gripper(gripper, position, duration=1.0):
    # Positions prédéfinies pour chaque gripper et position
    positions = {
        1: {
            "left": [1.0, 1.0],
            "right": [1.0, 1.0]
        },
        2: {
            "left": [0.0, 0.0],
            "right": [0.0, 0.0]
        }
    }
    
    if gripper not in ["left", "right"]:
        rospy.logerr("Erreur : gripper doit être 'left' ou 'right'")
        return False
    
    if position not in [1, 2]:
        rospy.logerr("Erreur : position doit être 1 ou 2")
        return False
    
    # Sélectionner le topic selon le gripper
    topic = f"/gripper_{gripper}_controller/command"
    pub = rospy.Publisher(
        topic,
        JointTrajectory,
        queue_size=10
    )

    # Attendre que le publisher se connecte aux subscribers
    rospy.sleep(2.0)
    while pub.get_num_connections() == 0 and not rospy.is_shutdown():
        rospy.sleep(0.1)

    traj = JointTrajectory()
    traj.header.stamp = rospy.Time(0)
    traj.joint_names = [
        f"gripper_{gripper}_right_finger_joint",
        f"gripper_{gripper}_left_finger_joint"
    ]
    
    # Récupérer les positions pour le gripper et la position donnés
    joint_values = positions[position][gripper]
    
    point = JointTrajectoryPoint()
    point.positions = joint_values
    point.time_from_start = rospy.Duration(duration)

    traj.points.append(point)
    pub.publish(traj)
    rospy.sleep(0.5)

    rospy.loginfo(f"Gripper {gripper} position {position} envoyée")

""" if __name__ == "__main__":
    rospy.init_node("gripper_left_command_node")
    move_gripper(args.gripper, args.position)
    rospy.spin() """