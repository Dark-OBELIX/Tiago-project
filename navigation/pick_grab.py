import rospy
import moveit_commander
import movegrip
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
class pick_grab:
    def __init__(self):
        """
        Séquence PICK & GRAB pour le bras droit de TIAGo
        Initialise MoveIt, ROS et les groupes de mouvement nécessaires
        """
        rospy.init_node("pick_grab", anonymous=True)
        self.robot = moveit_commander.RobotCommander()
        self.move_group_arm_right = moveit_commander.MoveGroupCommander("arm_right")
        self.move_group_torso = moveit_commander.MoveGroupCommander("torso")
        print("✓ Robot initialisé")
    def move_head(self, yaw, pitch, duration=2.0):
        """
        Bouge la tête de TIAGo

        :param yaw: rotation gauche/droite (rad) → head_1_joint
        :param pitch: haut/bas (rad) → head_2_joint
        :param duration: durée du mouvement (s)
        """

        pub = rospy.Publisher(
            '/head_controller/command',
            JointTrajectory,
            queue_size=1
        )

        rospy.sleep(0.5)  # laisser le temps au publisher de se connecter

        traj = JointTrajectory()
        traj.joint_names = ['head_1_joint', 'head_2_joint']

        point = JointTrajectoryPoint()
        point.positions = [yaw, pitch]
        point.time_from_start = rospy.Duration(duration)

        traj.points.append(point)

        pub.publish(traj)
    def move_torso(self, niveau):
        """
        Déplace le torse à un niveau prédéfini

        niveaux possibles :
        - high
        - neutral
        - low
        """
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
        Déplace le bras vers une position prédéfinie (PICK & GRAB)

        Bras utilisé :
        - right uniquement

        Positions disponibles :
        1 : position intermédiaire avant saisie
        2 : position de saisie (objet au milieu)
        3 : tirer l'objet vers soi
        4 : position regarder le bras
        """
        positions = {
            1: {
                "right": [0.21, -0.05, 1.51, 
                          1.71, -1.38, 1.31, 0.0]},
            2: {
                "right": [1.28, 0.2, 1.44, 
                          1.73, -1.59, -1.33, -0.16]
            },
            3 : {
                "right": [1.13, 0.12, 1.45, 
                          2.23, -1.58, -1.39, -0.17]
            },
            4: {
                "right": [0.79, -0.4, 1.39,
                          1.88, -2.07, 0.14, -0.18]
            },
            
            
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
        return True
def main(position):
    move = pick_grab()
    move.move_arm('right', 1)
    if position == 3 : 
        move.move_torso('high')
    elif position == 1:
        move.move_torso('low')
    else : 
        move.move_torso('neutral')
    move.move_arm('right', 2)
    movegrip.move_gripper('right', 2)  # Fermer la pince pour saisir
    rospy.sleep(2)
    move.move_arm('right', 3)
    move.move_arm('right', 4)
    move.move_head(0,-0.35)
    rospy.sleep(4)
    move.move_head(0,0)

if __name__ == "__main__":
    main(3)