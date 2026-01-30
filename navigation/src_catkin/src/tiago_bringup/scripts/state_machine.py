#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import rospy
import sys
import smach
import smach_ros
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from geometry_msgs.msg import Twist
from std_srvs.srv import Trigger, TriggerRequest
import math
import tf2_ros
import tf.transformations as tf_trans

# Variable globale pour le buffer TF
tfBuffer = None

# CLASSE ETAT : DEMANDER INPUT UTILISATEUR
class AskUser(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['succeeded', 'aborted'], output_keys=['aruco_id_out'])

    def execute(self, userdata):
        rospy.loginfo("ATTENTE INPUT UTILISATEUR...")
        try:
            # Compatibilite Python 2/3
            if sys.version_info[0] < 3:
                val = raw_input(">>> Entrez l'ID de l'ArUco a atteindre: ")
            else:
                val = input(">>> Entrez l'ID de l'ArUco a atteindre: ")
            
            chosen_id = int(val)
            rospy.loginfo(f"ID selectionne : {chosen_id}")
            userdata.aruco_id_out = chosen_id
            return 'succeeded'
        except ValueError:
            rospy.logerr("Entree invalide ! Veuillez entrer un nombre entier.")
            return 'aborted'
        except Exception as e:
            rospy.logerr(f"Erreur input: {e}")
            return 'aborted'

# Fonction pour preparer la requete de service (set param)
def set_aruco_param_cb(userdata, request):
    # On set le parametre global '/aruco_to_dock'
    rospy.set_param('/aruco_to_dock', userdata.aruco_id_in)
    rospy.loginfo(f"Parametre /aruco_to_dock mis a jour a : {userdata.aruco_id_in}")
    return TriggerRequest() # Requete vide

# CLASSE ETAT : CHOISIR POSITION PICK (1, 2, 3)
class AskPickPos(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['succeeded', 'aborted'], output_keys=['pick_pos_out'])

    def execute(self, userdata):
        rospy.loginfo("ATTENTE CHOIX POSITION (1, 2, 3)...")
        try:
            if sys.version_info[0] < 3:
                val = raw_input(">>> Position a saisir (1, 2, 3): ")
            else:
                val = input(">>> Position a saisir (1, 2, 3): ")
            
            p = int(val)
            if p not in [1, 2, 3]:
                 rospy.logwarn("Entree invalide (doit etre 1, 2 ou 3). Defaut = 1")
                 p = 1
            
            userdata.pick_pos_out = p
            return 'succeeded'
        except ValueError:
            return 'aborted'

# CLASSE ETAT : CHOISIR ACTION (JETER / DEPOSER)
class AskAction(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['jeter', 'deposer', 'aborted'])

    def execute(self, userdata):
        rospy.loginfo("QUE FAIRE ? (j)eter ou (d)eposer ?")
        try:
            if sys.version_info[0] < 3:
                val = raw_input(">>> Action (j/d): ")
            else:
                val = input(">>> Action (j/d): ")
            
            v = val.lower().strip()
            if v.startswith('j'):
                return 'jeter'
            elif v.startswith('d'):
                return 'deposer'
            else:
                return 'aborted'
        except:
            return 'aborted'

# Callback pour parametrer PickGrab
def set_pick_grab_param_cb(userdata, request):
    rospy.set_param('/pick_grab_position', userdata.pick_pos_in)
    return TriggerRequest()

# Callback pour parametrer ArUco Home (27)
def set_aruco_home_cb(userdata, request):
    rospy.set_param('/aruco_to_dock', 27)
    return TriggerRequest()

# Fonction callback qui genere un goal pour faire un 180 deg
def turn_180_goal_cb(userdata, default_goal):
    global tfBuffer
    goal = MoveBaseGoal()
    goal.target_pose.header.frame_id = "map"
    goal.target_pose.header.stamp = rospy.Time.now()
    print("debug: Generating 180 degree turn goal...")
    
    try:
        # On recupere la position actuelle du robot dans la map
        # "base_footprint" est souvent le repere au sol du robot
        transform = tfBuffer.lookup_transform("map", "base_footprint", rospy.Time(0), rospy.Duration(1.0))
        
        # 1. On garde la meme position (X, Y)
        goal.target_pose.pose.position.x = transform.transform.translation.x
        goal.target_pose.pose.position.y = transform.transform.translation.y
        goal.target_pose.pose.position.z = 0.0 # Toujours 0 au sol

        # 2. On recupere l'orientation actuelle
        rot = transform.transform.rotation
        # Conversion Quaternion -> Euler (Roll, Pitch, Yaw)
        (r, p, y) = tf_trans.euler_from_quaternion([rot.x, rot.y, rot.z, rot.w])
        
        # 3. On ajoute PI (180 degres) au Yaw
        y += math.pi
        
        # Conversion Euler -> Quaternion
        q_new = tf_trans.quaternion_from_euler(r, p, y)
        
        goal.target_pose.pose.orientation.x = q_new[0]
        goal.target_pose.pose.orientation.y = q_new[1]
        goal.target_pose.pose.orientation.z = q_new[2]
        goal.target_pose.pose.orientation.w = q_new[3]
        
        rospy.loginfo("Goal 180 degres genere avec succes.")
        
    except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException):
        rospy.logwarn("Impossible de recuperer la pose du robot pour le demi-tour !")
    
    return goal

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
    time.sleep(1)
    
    return goal

def main():
    global tfBuffer
    rospy.init_node('smach_modular_example')

    # Initialisation TF listener pour le calcul du demi-tour
    tfBuffer = tf2_ros.Buffer()
    listener = tf2_ros.TransformListener(tfBuffer)

    sm = smach.StateMachine(outcomes=['SUCCESS', 'FAILURE'])

    # --- DEFINITION DES PARAMETRES ---
    # On stocke tes coordonnées précises dans la mémoire globale de la machine
    # Format: [x, y, z, qx, qy, qz, qw]
    
    # Point 1 (Tes valeurs)
    sm.userdata.point_depart = [0.008, 0.85, 0.0, 0.0, 0.0, -0.36, 0.932]
    
    # Point 2 (Exemple d'un autre point pour tester)
    sm.userdata.point_retour = [0.002, 1.1, 0.0, 0.0, 0.0, -0.39, 0.92]

    # ID pour le retour a la maison
    sm.userdata.aruco_home = 27

    with sm:
        # ÉTAT 1 : ALLER AU POINT A
        smach.StateMachine.add('ALLER_POINT_A',
                               smach_ros.SimpleActionState(
                                   'move_base',
                                   MoveBaseAction,
                                   goal_cb=make_goal_from_userdata,
                                   input_keys=['target_pose_list']
                               ),
                               remapping={'target_pose_list': 'point_depart'},
                               transitions={'succeeded': 'ASK_USER', 
                                            'aborted': 'FAILURE', 
                                            'preempted': 'FAILURE'}
                               )

        # ÉTAT 2 : DEMANDER ID ARUCO
        smach.StateMachine.add('ASK_USER',
                               AskUser(),
                               transitions={'succeeded': 'SERVICE_DOCKING', 
                                            'aborted': 'FAILURE'},
                               remapping={'aruco_id_out': 'aruco_target'}
                               )

        # ÉTAT 3 : SERVICE DOCKING (VERS STAND CHOISI)
        smach.StateMachine.add('SERVICE_DOCKING',
                               smach_ros.ServiceState('/start_aruco_docking',
                                                      Trigger,
                                                      request_cb=set_aruco_param_cb,
                                                      input_keys=['aruco_id_in']),
                               transitions={'succeeded': 'ASK_PICK_POS',
                                            'aborted': 'FAILURE',
                                            'preempted': 'FAILURE'},
                               remapping={'aruco_id_in': 'aruco_target'}
                               )
        
        # ÉTAT 4 : DEMANDER POSITION PICK (1, 2, 3)
        smach.StateMachine.add('ASK_PICK_POS',
                               AskPickPos(),
                               transitions={'succeeded': 'PICK_GRAB',
                                            'aborted': 'FAILURE'},
                               remapping={'pick_pos_out': 'pick_pos'}
                               )

        # ÉTAT 5 : PICK & GRAB
        smach.StateMachine.add('PICK_GRAB',
                               smach_ros.ServiceState('/start_pick_grab',
                                                      Trigger,
                                                      request_cb=set_pick_grab_param_cb,
                                                      input_keys=['pick_pos_in']),
                               transitions={'succeeded': 'ASK_ACTION',
                                            'aborted': 'FAILURE',
                                            'preempted': 'FAILURE'},
                               remapping={'pick_pos_in': 'pick_pos'}
                               )

        # ÉTAT 6 : DEMANDER ACTION (JETER / DEPOSER)
        smach.StateMachine.add('ASK_ACTION',
                               AskAction(),
                               transitions={'jeter': 'VERIF_JETER',
                                            'deposer': 'VERIF_DEPOSER',
                                            'aborted': 'FAILURE'}
                               )

        # ÉTAT 7a : VERIF JETER
        smach.StateMachine.add('VERIF_JETER',
                               smach_ros.ServiceState('/start_jeter', Trigger),
                               transitions={'succeeded': 'JETER_HOMING_STAND',
                                            'aborted': 'FAILURE',
                                            'preempted': 'FAILURE'}
                               )

        # ÉTAT 7a-bis : JETER HOMING (Intermediaire)
        smach.StateMachine.add('JETER_HOMING_STAND',
                               smach_ros.ServiceState('/start_jeter_homing', Trigger),
                               transitions={'succeeded': 'FAIRE_DEMI_TOUR_STAND',
                                            'aborted': 'FAILURE',
                                            'preempted': 'FAILURE'}
                               )

        # ÉTAT 7b : VERIF DEPOSER
        smach.StateMachine.add('VERIF_DEPOSER',
                               smach_ros.ServiceState('/start_deposer_client', Trigger),
                               transitions={'succeeded': 'FAIRE_DEMI_TOUR_STAND',
                                            'aborted': 'FAILURE',
                                            'preempted': 'FAILURE'}
                               )

        # ÉTAT 8 : DEMI-TOUR AU STAND
        smach.StateMachine.add('FAIRE_DEMI_TOUR_STAND',
                               smach_ros.SimpleActionState(
                                   'move_base',
                                   MoveBaseAction,
                                   goal_cb=turn_180_goal_cb, 
                               ),
                               transitions={'succeeded': 'SERVICE_DOCKING_HOMESTATION',
                                            'aborted': 'FAILURE',
                                            'preempted': 'FAILURE'}
                               )

        # ÉTAT 9 : SERVICE DOCKING (VERS HOMESTATION ID 27)
        smach.StateMachine.add('SERVICE_DOCKING_HOMESTATION',
                               smach_ros.ServiceState('/start_aruco_docking',
                                                      Trigger,
                                                      request_cb=set_aruco_home_cb),
                               transitions={'succeeded': 'VERIF_JETER_FINAL',
                                            'aborted': 'FAILURE',
                                            'preempted': 'FAILURE'}
                               )

        # ÉTAT 10 : VERIF JETER FINAL
        smach.StateMachine.add('VERIF_JETER_FINAL',
                               smach_ros.ServiceState('/start_jeter', Trigger),
                               transitions={'succeeded': 'JETER_HOMING',
                                            'aborted': 'FAILURE',
                                            'preempted': 'FAILURE'}
                               )

        # ÉTAT 11 : JETER HOMING
        smach.StateMachine.add('JETER_HOMING',
                               smach_ros.ServiceState('/start_jeter_homing', Trigger),
                               transitions={'succeeded': 'SUCCESS',
                                            'aborted': 'FAILURE',
                                            'preempted': 'FAILURE'}
                               )

    sis = smach_ros.IntrospectionServer('server', sm, '/SM_ROOT')
    sis.start()
    outcome = sm.execute()
    rospy.spin()
    sis.stop()

if __name__ == '__main__':
    main()
