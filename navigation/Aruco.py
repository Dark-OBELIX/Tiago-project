import cv2
import cv2.aruco as aruco
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class ArUcoReader:
    def __init__(self):
        self.bridge = CvBridge()
        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        self.params = aruco.DetectorParameters_create()
        

        self.found_ids = set()
        

        self.sub = rospy.Subscriber("/xtion/rgb/image_raw", Image, self.image_cb)

    def image_cb(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = aruco.detectMarkers(gray, self.aruco_dict, parameters=self.params)

            if ids is not None:
                flat_ids = ids.flatten()
                for i in flat_ids:
                    self.found_ids.add(i) 
                    

            # cv2.imshow("Vue Robot", frame)
            # cv2.waitKey(1)

        except Exception as e:
            pass # On ignore les erreurs d'image pour ne pas spammer

    def is_id_detected(self, target_id):
        """ Vérifie si l'ID cible est dans la liste des trouvés """
        return target_id in self.found_ids
    
    def get_all_ids(self):
        return list(self.found_ids)