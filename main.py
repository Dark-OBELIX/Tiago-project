#!/usr/bin/env python3
import os

# ================== SUPPRESSION DES WARNINGS TENSORFLOW ==================
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"        # force CPU
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"         # cache logs TF
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"        # cache oneDNN

# ================== IMPORTS ==================
import rospy
import cv2
import random
import time
from collections import Counter

from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from deepface import DeepFace
from pal_interaction_msgs.msg import TtsActionGoal

# ================== CITATIONS ==================
QUOTES = {
    "happy": [
        "Je détecte que vous êtes joyeux, n'oubliez pas que la joie est un signe discret que tu avances dans la bonne direction.",
        "Je détecte que vous êtes joyeux, n'oubliez pas que quand la joie passe, laisse-la te rappeler ce qui compte vraiment.",
        "Je détecte que vous êtes joyeux, n'oubliez pas que la joie n’efface pas le reste : elle l’éclaire.",
        "Je détecte que vous êtes joyeux, n'oubliez pas de garder cette joie comme une boussole, pas comme une destination.",
    ],
    "sad": [
        "Je détecte que vous êtes triste, n'oubliez pas que la tristesse n’est pas un échec : c’est une profondeur qui parle.",
        "Je détecte que vous êtes triste, n'oubliez pas que parfois, le cœur ralentit pour comprendre.",
        "Je détecte que vous êtes triste, n'oubliez pas que la tristesse est un passage, pas une identité.",
        "Je détecte que vous êtes triste, n'oubliez pas que même la pluie a une utilité : elle prépare le sol.",
    ],
    "angry": [
        "Je détecte que vous êtes en colère, n'oubliez pas que la colère est une énergie : à vous de choisir où elle va.",
        "Je détecte que vous êtes en colère, n'oubliez pas que la colère éclaire un besoin, mais ne donne pas toujours la solution.",
        "Je détecte que vous êtes en colère, n'oubliez pas que respirer, c’est reprendre le contrôle.",
        "Je détecte que vous êtes en colère, n'oubliez pas que la colère est un feu : apprivoisé, il réchauffe; lâché, il brûle.",
    ],
    "neutral": [
        "Je ne détecte pas d'émotion particulière chez vous, n'oubliez pas que le calme est une forme de force : rien à prouver, tout à construire.",
        "Je ne détecte pas d'émotion particulière chez vous, n'oubliez pas que la neutralité, c’est parfois l’équilibre retrouvé.",
        "Je ne détecte pas d'émotion particulière chez vous, n'oubliez pas que dans le silence, on entend mieux l’essentiel.",
        "Je ne détecte pas d'émotion particulière chez vous, n'oubliez pas que la stabilité, c’est un point d’appui pour la suite.",
    ],
}

ALLOWED = ["angry", "happy", "sad", "neutral"]

# ================== PARAMS ONE-SHOT ==================
CAPTURE_SECONDS = 3.0
ANALYZE_EVERY_N_FRAMES = 5
IMAGE_TOPIC = "/xtion/rgb/image_raw"
SHOW_WINDOW = False  # mets False sur robot si pas d'affichage
NODE_NAME = "emotion_one_shot_tiago"

# ================== GLOBALS ==================
bridge = CvBridge()
tts_pub = None

latest_frame = None
frame_ready = False

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ================== TTS ==================
def say_text(text, lang="fr_FR"):
    global tts_pub
    if tts_pub is None:
        tts_pub = rospy.Publisher("/tts/goal", TtsActionGoal, queue_size=1)
        rospy.sleep(1)

    msg = TtsActionGoal()
    msg.goal.rawtext.text = text
    msg.goal.rawtext.lang_id = lang
    tts_pub.publish(msg)
    rospy.loginfo(f"TTS: {text}")

# ================== HELPERS ==================
def pick_quote(emotion: str) -> str:
    if emotion not in QUOTES:
        emotion = "neutral"
    return random.choice(QUOTES[emotion])

def normalize_emotion(raw_emotions: dict) -> str:
    filtered = {k: raw_emotions.get(k, 0.0) for k in ALLOWED}
    boost = {
        "angry": 10.0,
        "sad": 1.0,
        "happy": 1.0,
        "neutral": 0.75
    }
    adjusted = {emo: filtered[emo] * boost.get(emo, 1.0) for emo in filtered}
    return max(adjusted, key=adjusted.get)

def extract_face(frame_bgr):
    frame = cv2.resize(frame_bgr, (960, 540))
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return None, frame, faces

    (x, y, w, h) = faces[0]
    margin = 20
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(frame.shape[1], x + w + margin)
    y2 = min(frame.shape[0], y + h + margin)
    face = frame[y1:y2, x1:x2]
    return face, frame, faces

# ================== IMAGE CALLBACK ==================
def image_cb(msg):
    global latest_frame, frame_ready
    try:
        latest_frame = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        frame_ready = True
    except Exception as e:
        rospy.logerr(e)

# ================== MAIN ==================
def on_shutdown():
    if SHOW_WINDOW:
        cv2.destroyAllWindows()

def main():
    rospy.init_node(NODE_NAME, anonymous=False)
    rospy.on_shutdown(on_shutdown)

    rospy.Subscriber(IMAGE_TOPIC, Image, image_cb, queue_size=1)

    # Attend au moins une frame (max 2s)
    t0 = time.time()
    while not rospy.is_shutdown() and not frame_ready and (time.time() - t0) < 2.0:
        rospy.sleep(0.05)

    if not frame_ready:
        say_text("Je n'arrive pas à récupérer l'image de la caméra.")
        return

    emotions_detected = []
    frame_count = 0

    start = time.time()
    rate = rospy.Rate(30)

    while not rospy.is_shutdown() and (time.time() - start) < CAPTURE_SECONDS:
        if latest_frame is None:
            rate.sleep()
            continue

        frame_count += 1
        if frame_count % ANALYZE_EVERY_N_FRAMES != 0:
            # Affichage optionnel
            if SHOW_WINDOW:
                _, disp, faces = extract_face(latest_frame)
                for (x, y, w, h) in faces:
                    cv2.rectangle(disp, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.imshow("Emotion Robot (one-shot)", disp)
                cv2.waitKey(1)
            rate.sleep()
            continue

        face, disp, faces = extract_face(latest_frame)
        if SHOW_WINDOW:
            for (x, y, w, h) in faces:
                cv2.rectangle(disp, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.imshow("Emotion Robot (one-shot)", disp)
            cv2.waitKey(1)

        if face is None:
            rate.sleep()
            continue

        try:
            result = DeepFace.analyze(
                face,
                actions=["emotion"],
                enforce_detection=False
            )
            raw_emotions = result[0]["emotion"]
            emo = normalize_emotion(raw_emotions)
            emotions_detected.append(emo)
        except Exception as e:
            rospy.logwarn(f"Emotion error: {e}")

        rate.sleep()

    # Décision finale
    if len(emotions_detected) == 0:
        final_emotion = "neutral"
    else:
        final_emotion = Counter(emotions_detected).most_common(1)[0][0]

    quote = pick_quote(final_emotion)

    # Envoie au TTS puis stop
    say_text(quote)

    rospy.loginfo(f"Final emotion: {final_emotion} | Quote sent. Node will exit.")

if __name__ == "__main__":
    main()
