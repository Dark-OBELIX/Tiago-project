#!/usr/bin/env python3
import rospy
import cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from deepface import DeepFace

bridge = CvBridge()

analysis_interval = 30
frame_count = 0
last_emotion = "neutral"

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def image_cb(msg):
    global frame_count, last_emotion

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
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(frame.shape[1], x + w + margin)
        y2 = min(frame.shape[0], y + h + margin)
        face = frame[y1:y2, x1:x2]
        face = cv2.resize(face, (224, 224))

        try:
            result = DeepFace.analyze(
                face,
                actions=['emotion'],
                enforce_detection=False
            )

            raw_emotions = result[0]['emotion']

            allowed = ['angry', 'happy', 'sad', 'neutral']
            filtered = {k: v for k, v in raw_emotions.items() if k in allowed}

            boost = {
                'angry': 50.0,
                'sad': 1.0,
                'happy': 1.0,
                'neutral': 0.75
            }

            adjusted = {
                emo: score * boost.get(emo, 1.0)
                for emo, score in filtered.items()
            }

            last_emotion = max(adjusted, key=adjusted.get)

            print("RAW:", raw_emotions)
            print("ADJUSTED:", adjusted)
            print("FINAL:", last_emotion)
            print("------------")

        except Exception as e:
            rospy.logwarn(f"Emotion analysis error: {e}")

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    cv2.putText(
        frame,
        f"Emotion: {last_emotion}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("Live Emotion Detection", frame)
    cv2.waitKey(1)

    frame_count += 1


def on_shutdown():
    cv2.destroyAllWindows()


def main():
    rospy.init_node("emotion_detection_camera")
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
