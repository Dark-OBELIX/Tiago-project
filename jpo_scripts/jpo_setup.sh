#!/bin/bash

echo "=========================================="
echo "   CONFIGURATION TIAGO - MODE JPO"
echo "=========================================="

# 1. DESACTIVER LE HEAD MANAGER
# Cela empêche le robot de regarder les gens ou de bouger la tête tout seul.
# Sur Tiago, le nœud s'appelle souvent pal_head_manager ou head_manager.
echo "[1/4] Désactivation du Head Manager..."
rosnode kill /pal_head_manager 2>/dev/null || echo "pal_head_manager déjà éteint ou introuvable"
rosnode kill /head_manager 2>/dev/null || echo "head_manager déjà éteint ou introuvable"

# 2. CHANGER LA CARTE
# On tue l'ancien map_server et on en lance un nouveau avec ta carte JPO.
echo "[2/4] Chargement de la carte JPO..."
rosnode kill /map_server
sleep 2 # Pause pour laisser le temps au nœud de mourir

# Lancement du nouveau map_server en arrière-plan (&)
# Note : On utilise $HOME pour être sûr du chemin
if [ -f "$HOME/carte_jpo.yaml" ]; then
    rosrun map_server map_server "$HOME/carte_jpo.yaml" &
    echo " -> Nouvelle carte chargée : $HOME/carte_jpo.yaml"
else
    echo "ERREUR : Le fichier $HOME/carte_jpo.yaml n'existe pas !"
    exit 1
fi
sleep 3 # Pause pour laisser la carte se publier

# 3. REDUIRE LE RAYON D'INFLATION (Radius Collision)
# On réduit la zone de sécurité pour que le robot ose passer près des gens/stands.
# Valeur par défaut souvent 0.55 ou 0.6. On passe à 0.3 ou 0.35.
echo "[3/4] Réduction des marges de sécurité (Inflation Radius)..."

# Global Costmap (Planification lointaine)
rosrun dynamic_reconfigure dynparam set /move_base/global_costmap/inflation_layer inflation_radius 0.35
# Local Costmap (Évitement immédiat)
rosrun dynamic_reconfigure dynparam set /move_base/local_costmap/inflation_layer inflation_radius 0.30

echo " -> Inflation Radius réduit à 0.35m (Global) et 0.30m (Local)"

# 4. NETTOYAGE FINAL
# On force move_base à nettoyer ses mémoires tampons pour prendre en compte 
# la nouvelle carte et les nouveaux réglages immédiatement.
echo "[4/4] Reset des Costmaps..."
rosservice call /move_base/clear_costmaps "{}"

echo "=========================================="
echo "=========================================="