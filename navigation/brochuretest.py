#!/usr/bin/env python3
import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO

class BrochureDetector:
    def __init__(self, model_path="best_brochure.pt", conf_threshold=0.55):
        # Configuration
        self.bridge = CvBridge()
        self.conf_threshold = conf_threshold
        self.imgsz = 640
        self.conf_eps = 0.02
        
        # Chargement du modèle (une seule fois)
        rospy.loginfo(f"Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)
        
        # État mémoire
        self.prev_detected = False
        self.prev_conf = None

    def get_color_name(self, roi_bgr):
        """Identifie la couleur dominante en HSV."""
        if roi_bgr is None or roi_bgr.size == 0:
            return "unknown"

        roi = cv2.resize(roi_bgr, (240, 240), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        mask = (s > 70) & (v > 70)
        if np.count_nonzero(mask) < 800:
            return "unknown"

        h_med = int(np.median(h[mask]))

        if 18 <= h_med <= 35:
            return "jaune"
        elif 36 <= h_med <= 85:
            return "vert"
        elif 90 <= h_med <= 130:
            return "bleu"
        elif h_med >= 160 or h_med <= 10:
            return "rose" # Adapté selon tes besoins (pink-red)
        else:
            return "unknown"

    def analyze_frame(self, frame_bgr):
        """
        Exécute YOLO, annote l'image et retourne (image_annotée, nom_couleur)
        """
        annotated = frame_bgr.copy()
        results = self.model.predict(frame_bgr, conf=self.conf_threshold, imgsz=self.imgsz, verbose=False)
        r = results[0]

        # Cas : Aucune détection
        if r.boxes is None or len(r.boxes) == 0:
            if self.prev_detected:
                rospy.loginfo("Brochure lost ❌")
                self.prev_detected = False
                self.prev_conf = None
            return annotated, None

        # Cas : Meilleure détection
        best = max(r.boxes, key=lambda b: float(b.conf[0]))
        det_conf = float(best.conf[0])

        # Logique de log
        if not self.prev_detected:
            rospy.loginfo(f"Brochure detected ✅ (conf={det_conf:.2f})")
        elif self.prev_conf is not None and abs(det_conf - self.prev_conf) > self.conf_eps:
            # On met à jour sans forcément loguer à chaque fois pour ne pas spammer
            pass

        self.prev_detected = True
        self.prev_conf = det_conf

        # Coordonnées et ROI
        x1, y1, x2, y2 = map(int, best.xyxy[0].tolist())
        h, w = frame_bgr.shape[:2]
        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)

        roi = frame_bgr[y1:y2, x1:x2]
        cname = self.get_color_name(roi)

        # Dessin
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(annotated, f"{cname} ({det_conf:.2f})", (x1, max(0, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

        return annotated, cname

# --- Exemple d'utilisation dans le même fichier ---
if __name__ == "__main__":
    rospy.init_node("brochure_detector_node")
    detector = BrochureDetector()

    def image_callback(msg):
        bridge = CvBridge()
        frame = bridge.imgmsg_to_cv2(msg, "bgr8")
        img_out, couleur = detector.analyze_frame(frame)
        
        cv2.imshow("Vision Tiago", img_out)
        if couleur:
            print(f"Couleur vue : {couleur}")
        cv2.waitKey(1)

    rospy.Subscriber("/xtion/rgb/image_raw", Image, image_callback)
    rospy.spin()