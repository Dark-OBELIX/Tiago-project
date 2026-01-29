#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import smach
import smach_ros
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal

# Fonction utilitaire pour convertir une liste [x, y, z, qx, qy, qz, qw] en MoveBaseGoal
def make_goal_from_userdata(userdata, default_goal):
    goal = MoveBaseGoal()
    goal.target_pose.header.frame_id = "map"
    goal.target_pose.header.stamp = rospy.Time.now()

    # On récupère la liste passée en argument via userdata
    # La clé s'appelle 'target_pose_list' (définie dans input_keys plus bas)
    pose_data = userdata.target_pose_list

    # Position
    goal.target_pose.pose.position.x = pose_data[0]
    goal.target_pose.pose.position.y = pose_data[1]
    goal.target_pose.pose.position.z = pose_data[2]

    # Orientation
    goal.target_pose.pose.orientation.x = pose_data[3]
    goal.target_pose.pose.orientation.y = pose_data[4]
    goal.target_pose.pose.orientation.z = pose_data[5]
    goal.target_pose.pose.orientation.w = pose_data[6]

    return goal

def main():
    rospy.init_node('smach_modular_example')

    sm = smach.StateMachine(outcomes=['SUCCESS', 'FAILURE'])

    # --- DEFINITION DES PARAMETRES ---
    # On stocke tes coordonnées précises dans la mémoire globale de la machine
    # Format: [x, y, z, qx, qy, qz, qw]
    
    # Point 1 (Tes valeurs)
    sm.userdata.point_depart = [0.008, 0.85, 0.0, 0.0, 0.0, -0.36, 0.932]
    
    # Point 2 (Exemple d'un autre point pour tester)
    sm.userdata.point_retour = [0.002, 1.1, 0.0, 0.0, 0.0, -0.39, 0.92]

    with sm:
        # ÉTAT 1 : ALLER AU POINT SPECIFIQUE
        # On utilise SimpleActionState mais on lui injecte les données
        smach.StateMachine.add('ALLER_POINT_A',
                               smach_ros.SimpleActionState(
                                   'move_base',
                                   MoveBaseAction,
                                   goal_cb=make_goal_from_userdata, # La fonction de conversion
                                   input_keys=['target_pose_list']  # Ce que l'état attend
                               ),
                               # ICI on fait le lien : target_pose_list <-- point_depart
                               remapping={'target_pose_list': 'point_depart'},
                               transitions={'succeeded': 'SUCCESS', 
                                            'aborted': 'FAILURE', 
                                            'preempted': 'FAILURE'}
                               )

        # # ÉTAT 2 : RETOURNER (Même logique, mêmes paramètres, juste le mapping change)
        # smach.StateMachine.add('ALLER_RETOUR',
        #                        smach_ros.SimpleActionState(
        #                            'move_base',
        #                            MoveBaseAction,
        #                            goal_cb=make_goal_from_userdata,
        #                            input_keys=['target_pose_list']
        #                        ),
        #                        # ICI on fait le lien : target_pose_list <-- point_retour
        #                        remapping={'target_pose_list': 'point_retour'},
        #                        transitions={'succeeded': 'SUCCESS', 
        #                                     'aborted': 'FAILURE', 
        #                                     'preempted': 'FAILURE'}
        #                        )

    sis = smach_ros.IntrospectionServer('server', sm, '/SM_ROOT')
    sis.start()
    outcome = sm.execute()
    rospy.spin()
    sis.stop()

if __name__ == '__main__':
    main()