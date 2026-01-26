#!/usr/bin/env python3
"""
Script simple pour bouger le bras droit ou gauche du robot TiaGo
Utilisation : python3 move_arm_simple.py [left|right] [1|2]
Exemple : python3 move_arm_simple.py left 1
"""
import aruco_nav
from aruco_nav import ArucoDocker
import rospy
import moveit_commander
import sys
import movegrip
from Aruco import ArUcoSingleReader
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
class ArmMover:
    def __init__(self):
        # Initialiser MoveIt et ROS
        moveit_commander.roscpp_initialize(sys.argv)
        rospy.init_node("arm_mover", anonymous=True)
        self.position = 4
        self.robot = moveit_commander.RobotCommander()
        self.move_group_arm_left = moveit_commander.MoveGroupCommander("arm_left")
        self.move_group_arm_right = moveit_commander.MoveGroupCommander("arm_right")
        self.move_group_torso = moveit_commander.MoveGroupCommander("torso")
        print("✓ Robot initialisé")
    """ def move_head(self, pan=0.0, tilt=0.0):
        #pan: rotation gauche(+)/droite(-) (head_1_joint)
        #tilt: inclinaison haut(-)/bas(+) (head_2_joint)
        traj = JointTrajectory()
        traj.joint_names = ['head_1_joint', 'head_2_joint']
        
        point = JointTrajectoryPoint()
        point.positions = [pan, tilt]
        point.time_from_start = rospy.Duration(1.0) # Le mouvement prendra 1 seconde
        
        traj.points.append(point)
        self.head_pub.publish(traj)
        rospy.loginfo(f"Commande tête envoyée : pan={pan}, tilt={tilt}") """
    def count(self):
        self.counter+=1
    def move_torso(self, niveau):
        level = {
            "high": [0.265],
            "neutral":[0.2],
            "low":[0.135]
        }
        torso_move = self.move_group_torso
        torso_move.clear_pose_targets()
        torso_move.stop()

        torso_move.set_joint_value_target(level[niveau])
        torso_move.go(level[niveau], wait=True)
    def move_arm(self, arm, position):
        """
        Bouger le bras vers une position prédéfinie
        arm: "left" ou "right"
        position: 1 ou 2
        """
        # Positions prédéfinies
        """1 repos, 3 attraper milieu,4 tirer, 5 regarder bras, 6 déposer, 7 position intermediaire"""
        positions = {
            1: {
                "left": [-1.1001652770191288, 1.4679210480602556, 2.7139581408352638, 1.7092685314029974, -1.5709013012901742, 1.36994880082998, 0.00016342434524205425],
                "right": [-1.1001652770191288, 1.4679210480602556, 2.7139581408352638, 1.7092685314029974, -1.5709013012901742, 1.36994880082998, -0.00016342434524205425]
            },
            3: {
                "left": [1.28, 0.1, 1.44, 
                          1.73, -1.59, -1.33, -0.16],
                "right": [1.28, 0.1, 1.44, 
                          1.73, -1.59, -1.33, -0.16]
            },
            4: {
                "left": [1.13, 0.12, 1.45, 
                          2.23, -1.58, -1.39, -0.17],
                "right": [1.13, 0.12, 1.45, 
                          2.23, -1.58, -1.39, -0.17]
            },
            5: {
                "left": [0.9421578142999586,-0.21311409590575092, 1.4010525892851553, 
                         2.2242633924991946, 0.0, 0, 1.0],
                "right": [0.79, -0.4, 1.39,
                          1.88, -2.07, 0.14, -0.18]
            },
            6: {
                "left": [0.9421578142999586, 0.35, 1.4010525892851553, 
                          2.2242633924991946, -1.6781702963473467, -1.3937755123985682, -2.0],
                "right": [0.9421578142999586, 0.35, 1.4010525892851553, 
                          2.2242633924991946, -1.6781702963473467, -1.3937755123985682, -2.0]
            },
            7: {"left": [-1.11, 1.49, 2.81, 
                          1.65, 1.61, -0.95, -1.87],
                "right": [-1.11, 1.49, 2.81, 
                          1.65, 1.61, -0.95, -1.87]}
        }
        
        if arm not in ["left", "right"]:
            print("❌ Erreur : arm doit être 'left' ou 'right'")
            return False
        
        
        # Sélectionner le groupe de mouvement
        if arm == "left":
            move_group = self.move_group_arm_left
        else:
            move_group = self.move_group_arm_right
        
        # Nettoyer les cibles précédentes
        move_group.clear_pose_targets()
        move_group.stop()
        
        # Récupérer la position
        joint_values = positions[position][arm]
        
        print(f"Déplacement du bras {arm.upper()} vers la position {position}...")
        
        # Bouger le bras
        move_group.go(joint_values, wait=True)
        move_group.stop()
        
        print(f"✓ Bras {arm.upper()} déplacé avec succès!")
        
        # Exécuter movegrip après le déplacement du bras
        print("Exécution de movegrip...")
        """ if position == 1:
            movegrip.move_gripper(arm,2)  # Ouvrir la pince en position de repos
        if position in [2, 3, 4]:
            movegrip.move_gripper(arm,2)  # Fermer la pince pour saisir
        elif position == 6:
            movegrip.move_gripper(arm,2)  # Ouvrir la pince pour regarder """
        """ else:
            movegrip.move_gripper(arm, position) """
        
        return True

def pick_grab():
    """ detection = ArUcoSingleReader()
    detection.get_id(timeout=5.0)
    position = detection.get_id()
    print("IDs détectés :", position)
    if position in [24,25,26]:
        print("Marqueur détecté pour la position :", position)
        position = position - 22  # Convertir 24,25,26 en 2,3,4
    else: 
        position = position
    print("Position détectée :", position) """
    move = ArmMover()
    move.move_arm('right', 7)
    if move.position == 4 : 
        move.move_torso('high')
    elif move.position == 2:
        move.move_torso('low')
    else : 
        move.move_torso('neutral')
    move.move_arm('right', 3)
    movegrip.move_gripper('right', 2)  # Fermer la pince pour saisir
    move.move_arm('right', 4)
    move.move_arm('right', 5)
    move.position-=1
def homing():
    mover = ArmMover()
    mover.move_arm('right', 1)
    movegrip.move_gripper('right', 1)  # Ouvrir la pince en position de repos
    mover.move_torso('neutral')
def main():
    if len(sys.argv) < 3:
        print("Usage : python3 move_arm_simple.py [left|right] [1|2]")
        print("Exemples :")
        print("  python3 move_arm_simple.py left 1")
        print("  python3 move_arm_simple.py right 2")
        print("\nPositions disponibles :")
        print("  1 : Position de repos (bas)")
        print("  2 : Position intermédiaire (saisie)")
        sys.exit(1)
    
    arm = sys.argv[1].lower()
    try:
        position = int(sys.argv[2])
    except ValueError:
        print("❌ Erreur : la position doit être un nombre (1 ou 2)")
        sys.exit(1)
    
    try:
        mover = ArmMover()
        mover.move_arm(arm, position)
    except rospy.ROSInterruptException:
        print("❌ Nœud arrêté")

if __name__ == "__main__":
    try:
        node = ArucoDocker()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
    finally:
        cv2.destroyAllWindows()
    pick_grab()
    #homing()
    """ move = ArmMover()
    move.move_head(pan=0.0, tilt=-0.5) """
    #main()