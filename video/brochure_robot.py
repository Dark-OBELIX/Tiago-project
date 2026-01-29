#!/usr/bin/env python3
import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from std_msgs.msg import String  # <--- Import pour le texte
from cv_bridge import CvBridge
from ultralytics import YOLO

# ================== CONFIGURATION ==================
MODEL_PATH = "best_brochure.pt"
IMAGE_TOPIC = "/xtion/rgb/image_raw"
RESULT_TOPIC = "/brochure_color" # Le topic où on envoie le résultat

bridge = CvBridge()
latest_frame = None
frame_ready = False

def image_cb(msg):
    global latest_frame, frame_ready
    try:
        latest_frame = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        frame_ready = True
    except Exception as e:
        rospy.logerr(f"Erreur conversion: {e}")

def get_color_name(roi):
    if roi is None or roi.size == 0: return "inconnu"
    hsv = cv2.cvtColor(cv2.resize(roi, (50, 50)), cv2.COLOR_BGR2HSV)
    mask = (hsv[:,:,1] > 70) & (hsv[:,:,2] > 70)
    if np.count_nonzero(mask) < 50: return "inconnu"
    h_med = np.median(hsv[:,:,0][mask])
    if 18 <= h_med <= 35: return "jaune"
    if 36 <= h_med <= 85: return "vert"
    if 90 <= h_med <= 130: return "bleu"
    if h_med >= 160 or h_med <= 10: return "rose/rouge"
    return "inconnu"

def main():
    global latest_frame, frame_ready
    rospy.init_node("yolo_brochure_detector")
    
    # Initialisation du Publisher avec latch=True
    pub = rospy.Publisher(RESULT_TOPIC, String, queue_size=1, latch=True)
    
    model = YOLO(MODEL_PATH)
    rospy.Subscriber(IMAGE_TOPIC, Image, image_cb, queue_size=1)
    
    rospy.loginfo("Détecteur lancé. En attente d'une couleur valide...")
    rate = rospy.Rate(10)
    found = False

    while not rospy.is_shutdown() and not found:
        if not frame_ready or latest_frame is None:
            rate.sleep()
            continue

        results = model.predict(latest_frame, conf=0.55, imgsz=320, verbose=False)
        
        if len(results[0].boxes) > 0:
            best = max(results[0].boxes, key=lambda b: float(b.conf[0]))
            x1, y1, x2, y2 = map(int, best.xyxy[0].tolist())
            color = get_color_name(latest_frame[y1:y2, x1:x2])
            
            if color != "inconnu":
                rospy.loginfo(f"Couleur trouvée : {color}")
                
                # 1. On le met dans le serveur de paramètres (STOCKAGE)
                rospy.set_param('/brochure_color', color)
                
                # 2. On peut aussi le publier sur le topic si besoin (LIVE)
                pub.publish(color)
                
                found = True # Arrête le script
        
        rate.sleep()

if __name__ == "__main__":
    main()