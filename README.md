Git projet precedent : https://github.com/CESI-Robotics-Bdx-2425/Documentation/blob/master/INSTALL.md

A chaque appel de fichier python faire dans un 2eme terminal : 
source /opt/ros/noetic/setup.bash

Flux video lu direct avec ros : rosrun image_view image_view image:=/xtion/rgb/image_raw

user@Vador-2:~/custom_ws/src/tiago_custom_pkg/src/Tiago-project$ 

Par défaults le docker a pas pip :

sudo apt update && sudo apt install python3-pip -y
