#!/usr/bin/env python3
import os

# ================== SUPPRESSION DES WARNINGS TENSORFLOW ==================
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"        # force CPU
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"         # cache logs TF
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"        # cache oneDNN

# ================== IMPORTS ==================
import rospy
import cv2
import time
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from deepface import DeepFace
from pal_interaction_msgs.msg import TtsActionGoal

# ================== GLOBALS ==================
bridge = CvBridge()

analysis_interval = 40
frame_count = 0
last_emotion = "neutral"

last_spoken_emotion = None
last_speech_time = 0
SPEECH_COOLDOWN = 10  # secondes

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

tts_pub = None

# ================== TTS ==================
def say_text(text, lang="fr_FR"):
    global tts_pub

    if tts_pub is None:
        tts_pub = rospy.Publisher(
            "/tts/goal",
            TtsActionGoal,
            queue_size=1
        )
        rospy.sleep(1)

    msg = TtsActionGoal()
    msg.goal.rawtext.text = text
    msg.goal.rawtext.lang_id = lang
    tts_pub.publish(msg)

    rospy.loginfo(f"TTS : {text}")

# ================== EMOTION → PHRASE ==================
def emotion_to_sentence(emotion):
    return {
        "angry":   "Bonjour… vous semblez en colère. Est-ce que tout va bien ?",
        "sad":     "Bonjour… vous avez l'air un peu triste.",
        "happy":   "Bonjour ! Vous avez l'air très heureux aujourd'hui !",
        "neutral": "Bonjour."
    }.get(emotion, "Bonjour.")

# ================== IMAGE CALLBACK ==================
def image_cb(msg):
    global frame_count, last_emotion
    global last_spoken_emotion, last_speech_time

    try:
        frame = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
    except Exception as e:
        rospy.logerr(e)
        return

    frame = cv2.resize(frame, (960, 540))
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if frame_count % analysis_interval == 0 and len(faces) > 0:
        (x, y, w, h) = faces[0]
        margin = 20
        face = frame[
            max(0, y-margin):min(frame.shape[0], y+h+margin),
            max(0, x-margin):min(frame.shape[1], x+w+margin)
        ]
        face = cv2.resize(face, (224, 224))

        try:
            result = DeepFace.analyze(
                face,
                actions=["emotion"],
                enforce_detection=False
            )

            raw = result[0]["emotion"]

            allowed = ["angry", "happy", "sad", "neutral"]
            boost = {
                "angry": 50.0,
                "sad": 1.0,
                "happy": 1.0,
                "neutral": 0.75
            }

            adjusted = {
                emo: raw[emo] * boost.get(emo, 1.0)
                for emo in allowed
            }

            last_emotion = max(adjusted, key=adjusted.get)

            now = time.time()
            if (
                last_emotion != last_spoken_emotion
                and now - last_speech_time > SPEECH_COOLDOWN
            ):
                say_text(emotion_to_sentence(last_emotion))
                last_spoken_emotion = last_emotion
                last_speech_time = now

        except Exception as e:
            rospy.logwarn(f"Emotion error: {e}")

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)

    cv2.putText(
        frame,
        f"Emotion: {last_emotion}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("Emotion Robot", frame)
    cv2.waitKey(1)

    frame_count += 1

# ================== MAIN ==================
def on_shutdown():
    cv2.destroyAllWindows()

def main():
    rospy.init_node("emotion_social_robot")
    rospy.on_shutdown(on_shutdown)

    rospy.Subscriber(
        "/xtion/rgb/image_raw",
        Image,
        image_cb,
        queue_size=1
    )

    rospy.spin()

if __name__ == "__main__":
    main()
