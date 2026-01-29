#!/usr/bin/env python
import rospy
import actionlib
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal

def move_to_goal(x, y, w):
    # Initialisation du noeud
    rospy.init_node('send_goal_node')

    # Création du client vers move_base
    client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    
    # Attente du serveur
    rospy.loginfo("Attente du serveur move_base...")
    client.wait_for_server()

    # Définition du but
    goal = MoveBaseGoal()
    goal.target_pose.header.frame_id = "map" # Référence globale
    goal.target_pose.header.stamp = rospy.Time.now()
    
    # Coordonnées (Point fixe)
    goal.target_pose.pose.position.x = x
    goal.target_pose.pose.position.y = y
    
    # Orientation (Quaternion simplifié pour l'exemple, w=1.0 signifie 0 rotation)
    goal.target_pose.pose.orientation.w = w

    # Envoi
    rospy.loginfo(f"Envoi vers x={x}, y={y}")
    client.send_goal(goal)

    # Attente du résultat
    client.wait_for_result()
    return client.get_state()

if __name__ == '__main__':
    try:
        # Aller au point x=2.0, y=3.0
        result = move_to_goal(2.0, 3.0, 1.0)
        if result == 3:
            rospy.loginfo("But atteint !")
        else:
            rospy.loginfo("Echec.")
    except rospy.ROSInterruptException:
        pass