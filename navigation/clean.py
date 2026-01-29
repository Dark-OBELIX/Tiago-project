#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
from moveit_commander import PlanningSceneInterface
import sys

def clean_only():
    # Initialisation du node ROS
    rospy.init_node("clean_moveit_scene", anonymous=True)
    
    # Connexion à l'interface de la scène MoveIt
    scene = PlanningSceneInterface()
    rospy.sleep(1.0)  # Temps de connexion nécessaire

    # Récupération des objets présents
    objs = scene.get_known_object_names()
    attached = scene.get_attached_objects()

    if not objs and not attached:
        rospy.loginfo("✨ La scène est déjà vide.")
    else:
        rospy.loginfo(f"🧹 Suppression de {len(objs)} objets...")
        
        # Supprimer les objets attachés (grippers)
        for name in attached.keys():
            scene.remove_attached_object(name)
            
        # Supprimer les objets de collision (boxes)
        for name in objs:
            scene.remove_world_object(name)
            
        rospy.loginfo("✅ Scène nettoyée.")
        return
if __name__ == "__main__":
    try:
        clean_only()
    except rospy.ROSInterruptException:
        pass