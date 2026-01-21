#!/usr/bin/env python3
import rospy
from pal_interaction_msgs.msg import TtsActionGoal

def say_text(text, lang="fr_FR"):
    
    if not rospy.core.is_initialized():
        rospy.init_node("tts_python_publisher", anonymous=True)

    pub = rospy.Publisher(
        "/tts/goal",
        TtsActionGoal,
        queue_size=1
    )

    rospy.sleep(1)  # laisse le temps au publisher de se connecter

    msg = TtsActionGoal()
    msg.goal.rawtext.text = text
    msg.goal.rawtext.lang_id = lang

    pub.publish(msg)
    rospy.loginfo(f"TTS envoyé : '{text}'")


if __name__ == "__main__":
    say_text("bonjour arnaud")

