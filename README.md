# Installation Audio TIAGO (Docker)

Ce document décrit la configuration et l’installation nécessaires pour utiliser l’audio avec TIAGO dans un conteneur Docker.

---

## Référence du projet précédent

Documentation d’origine :
[https://github.com/CESI-Robotics-Bdx-2425/Documentation/blob/master/INSTALL.md](https://github.com/CESI-Robotics-Bdx-2425/Documentation/blob/master/INSTALL.md)

---

## Configuration Docker

Commande de lancement du conteneur Docker :

```bash
docker run -it \
-d \
-u user \
-e DISPLAY=$DISPLAY \
--network host \
--privileged \
-v /tmp/.X11-unix/:/tmp/.X11-unix/ \
-v $HOME/.config/pulse:/root/.config/pulse \
--device /dev/snd \
--name tiago-real-audio-usb \
docker_tiagocesi_image_full \
bash
```

---

## Installation des outils dans le conteneur

### Installation de pip

Par défaut, `pip` n’est pas installé dans le conteneur.

```bash
sudo apt update && sudo apt install -y python3-pip
```

---

## Installation des outils audio

Installer les utilitaires ALSA à l’intérieur du conteneur :

```bash
sudo apt-get update
sudo apt-get install -y alsa-utils
```

---

## Configuration du conteneur

Éditer le fichier `~/.bashrc` :

```bash
nano ~/.bashrc
```

Ajouter les lignes suivantes à la fin du fichier :

```bash
source /opt/pal/gallium/setup.bash
source /usr/share/cesi-tiago-package/behaviour_tree/ws_behaviotree/devel/setup.bash

export ROS_MASTER_URI=http://10.68.0.1:11311   # Adapter selon le robot utilisé
export ROS_IP=10.68.0.131                     # Adapter selon l’adresse IP du conteneur
```

Recharger la configuration :

```bash
source ~/.bashrc
```

---

## Remarque

En cas de problèmes lors de l’exécution de scripts Python, il peut être nécessaire de sourcer explicitement ROS Noetic :

```bash
source /opt/ros/noetic/setup.bash
```

Avant de démarer chaque conteneur faire dans un terminal sur le pc hote :
```bash
xhost +local:
```
