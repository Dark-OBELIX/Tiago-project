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
from std_srvs.srv import Trigger, TriggerResponse

class ArmMover:
    def __init__(self):
        # Initialiser MoveIt et ROS
        moveit_commander.roscpp_initialize(sys.argv)
        rospy.init_node("deposer_client_service", anonymous=False)
        self.robot = moveit_commander.RobotCommander()
        self.move_group_arm_right = moveit_commander.MoveGroupCommander("arm_right")
        
        self.service = rospy.Service('start_deposer_client', Trigger, self.handle_service)
        rospy.loginfo("Service 'start_deposer_client' pret.")

    def handle_service(self, req):
        rospy.loginfo("Execution du service Deposer Client...")
        try:
            self.move_arm()
            return TriggerResponse(success=True, message="Deposer Client termine")
        except Exception as e:
            rospy.logerr(f"Erreur: {e}")
            return TriggerResponse(success=False, message=str(e))
        
    def move_arm(self):
        position = {
                1:{"right": [1.42, -0.04, -0.12, 
                          0.21, -1.12, -0.4, -0.03]},
                2:{"right": [1.42, -0.03, -0.13, 
                          1.49, -0.86, 0.04, -0.03]},
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
        rospy.spin()
    except rospy.ROSInterruptException:
        print("❌ Nœud arrêté")


if __name__ == "__main__":
    main()
