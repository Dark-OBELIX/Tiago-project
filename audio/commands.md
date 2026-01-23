*Création du conteneur Docker avec accès audio*

**Lancer le conteneur Docker avec les options nécessaires pour l’audio, PulseAudio et les périphériques USB :**

docker run -it
-d
-u user
-e DISPLAY=$DISPLAY
--network host
--privileged
-v /tmp/.X11-unix/:/tmp/.X11-unix/
-v $HOME/.config/pulse:/root/.config/pulse
--device /dev/snd
--name tiago-real-audio-usb
docker_tiagocesi_image_full
bash

Remarques :

L’option --device /dev/snd permet l’accès aux périphériques audio ALSA
L’option --privileged est nécessaire pour l’accès aux périphériques USB audio
Le montage PulseAudio permet la gestion du son côté hôte

**Installation des outils audio dans le conteneur**
Une fois à l’intérieur du conteneur, installer les utilitaires ALSA :

sudo apt-get update
sudo apt-get install -y alsa-utils

**Vérification de la détection du micro**

Lister les périphériques d’enregistrement disponibles :
arecord -l

Exemple de sortie attendue :
card 2: USB [USB Audio], device 0: USB Audio [USB Audio]

Le périphérique est alors accessible via hw:2,0

**Test du haut-parleur**

***Tester la sortie audio avec un signal sinusoïdal :***

speaker-test -D plughw:2,0 -t sine -f 440

Si le périphérique plughw:2,0 n’est pas valide, adapter les indices (plughw:0,0, plughw:1,0, etc.) en fonction des résultats de arecord -l et aplay -l.

***Enregistrement audio depuis le micro USB**

Enregistrer un fichier audio WAV de 10 secondes :

sudo arecord -D hw:2,0 -f S16_LE -c 1 -r 48000 -t wav -d 10 test_usb_mic.wav

Paramètres :

Format : 16 bits little-endian
Nombre de canaux : mono
Fréquence d’échantillonnage : 48 kHz
Durée : 10 secondes

**Lecture du fichier audio enregistré**

***Lecture du fichier audio :***
aplay test_usb_mic.wav

Ou depuis un autre répertoire :
aplay /home/Tiago-project/audio/test_files/test_usb_mic.wav

**Lancement des nœuds ROS audio**

Lancement de la capture audio (micro) :
roslaunch audio_capture capture.launch device:="plughw:0,0"

Lancement de la lecture audio (haut-parleur) :
roslaunch audio_play play.launch device:="plughw:2,0"

Les valeurs plughw:X,Y doivent être adaptées selon les périphériques détectés dans le conteneur.
