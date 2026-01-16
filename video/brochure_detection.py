#!/usr/bin/env python3
import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO

# ----------------------------
# Settings (you can also turn these into ROS params later)
# ----------------------------
MODEL_PATH = "best_brochure.pt"   # your YOLO weights
CONF = 0.55                       # raise (0.60-0.70) to reduce false positives
IMGSZ = 640                       # 640 good; 960 helps far objects (slower)
WINDOW = "Brochure + Color (press q to quit)"
TOPIC = "/xtion/rgb/image_raw"    # camera topic
# ----------------------------

bridge = CvBridge()
model = None  # will be loaded once in main()


def color_name_from_roi(roi_bgr: np.ndarray) -> str:
    """
    Simple color naming based on dominant hue in HSV, using only saturated/bright pixels.
    Returns: yellow / green / blue / pink-red / unknown
    """
    if roi_bgr is None or roi_bgr.size == 0:
        return "unknown"

    roi = cv2.resize(roi_bgr, (240, 240), interpolation=cv2.INTER_AREA)

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    mask = (s > 70) & (v > 70)
    if np.count_nonzero(mask) < 800:
        return "unknown"

    h_med = int(np.median(h[mask]))  # 0..179 (OpenCV hue)

    if 18 <= h_med <= 35:
        return "yellow"
    elif 36 <= h_med <= 85:
        return "green"
    elif 90 <= h_med <= 130:
        return "blue"
    elif h_med >= 160 or h_med <= 10:
        return "pink-red"
    else:
        return "unknown"


def annotate_brochure(frame_bgr: np.ndarray) -> np.ndarray:
    """
    Runs YOLO on frame, keeps best detection only, infers color from ROI,
    and returns an annotated frame.
    """
    global model
    annotated = frame_bgr.copy()

    if model is None:
        cv2.putText(
            annotated, "YOLO model not loaded",
            (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 255), 2
        )
        return annotated

    results = model.predict(frame_bgr, conf=CONF, imgsz=IMGSZ, verbose=False)
    r = results[0]

    if r.boxes is None or len(r.boxes) == 0:
        cv2.putText(
            annotated, "No brochure detected",
            (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 255), 2
        )
        return annotated

    # Keep best detection only
    best = max(r.boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = map(int, best.xyxy[0].tolist())
    det_conf = float(best.conf[0])

    # Clamp coords
    h, w = frame_bgr.shape[:2]
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(w, x2); y2 = min(h, y2)

    roi = frame_bgr[y1:y2, x1:x2]
    cname = color_name_from_roi(roi)

    # Draw box + label
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(
        annotated,
        f"brochure {det_conf:.2f} | {cname}",
        (x1, max(0, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 255, 0),
        2
    )
    return annotated


def image_cb(msg: Image):
    """
    Callback called each time a new image arrives from the ROS topic.
    """
    try:
        frame = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        annotated = annotate_brochure(frame)

        cv2.imshow(WINDOW, annotated)

        # Allow quitting with 'q'
        if cv2.waitKey(1) & 0xFF == ord("q"):
            rospy.signal_shutdown("User requested shutdown (pressed q).")

    except Exception as e:
        rospy.logerr(e)


def main():
    global model

    rospy.init_node("brochure_detector_viewer")

    # Load YOLO model once (important for speed!)
    rospy.loginfo(f"Loading YOLO model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    rospy.loginfo("YOLO model loaded ✅")

    rospy.Subscriber(
        TOPIC,
        Image,
        image_cb,
        queue_size=1
    )

    rospy.loginfo(f"Subscribed to {TOPIC}. Press 'q' on the OpenCV window to quit.")
    try:
        rospy.spin()
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
