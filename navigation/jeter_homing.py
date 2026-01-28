#!/usr/bin/env python3
"""
Script pour bouger le bras droit ou gauche du robot TiaGo
Utilisation : python3 move_arm_simple.py 
Exemple : python3 move_arm_simple.py 
"""
import rospy
import moveit_commander
import sys
import movegrip
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

class ArmMover:
    def __init__(self):
        # Initialiser MoveIt et ROS
        moveit_commander.roscpp_initialize(sys.argv)
        rospy.init_node("arm_mover", anonymous=True)
        self.robot = moveit_commander.RobotCommander()
        self.move_group_arm_right = moveit_commander.MoveGroupCommander("arm_right")
        
    def move_arm(self):
        position = {
                1:{"right": [1.42, -0.04, -0.12, 
                          0.21, -1.12, -0.4, -0.03]},
                2:{"right": [-1.1001652770191288, 1.4679210480602556,
                             2.7139581408352638, 1.7092685314029974,
                             -1.5709013012901742, 1.36994880082998,
                             -0.00016342434524205425]},
            }
        move_group = self.move_group_arm_right
        move_group.clear_pose_targets()
        move_group.stop()
        
        joint_values = position[1]["right"]
        # Bouger le bras
        move_group.go(joint_values, wait=True)
        move_group.stop()
        move_group = self.move_group_arm_right
        move_group.clear_pose_targets()
        move_group.stop()
        
        joint_values = position[2]["right"]
        # Bouger le bras
        move_group.go(joint_values, wait=True)
        move_group.stop()
        
        return True


def main():
    try:
        mover = ArmMover()
        mover.move_arm()
    except rospy.ROSInterruptException:
        print("❌ Nœud arrêté")


if __name__ == "__main__":
    main()