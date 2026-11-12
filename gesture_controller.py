#CONSTANTS
NOSE =0
LEFT_SHOULDER = 11
RIGHT_SHOULDER =12
LEFT_HIP =23
RIGHT_HIP =24

class GestureController:

    def __init__(self):
        self.min_visibility = 0.7 #the least visibility we accept 
        self.required_landmarks = [
        NOSE,
        LEFT_SHOULDER,
        RIGHT_SHOULDER,
        LEFT_HIP,
        RIGHT_HIP
        ]
        self.baseline = None 
        self.calibration_frames = 60 #60 correct features ready to be used
        self.calibration_samples = [] #60 features 
        self.is_calibrated = False #if we finished
        self.is_calibrating = False #if we are calibrating currently
        # self.jump_threshold = -0.08
        self.jump_threshold = -0.14
        self.jump_shoulder_threshold = -0.09
        self.slide_threshold = 0.08
        self.left_threshold = -0.08
        self.right_threshold = 0.08

    def is_landmark_visible(self, landmark): #method to make sure that the landmarks are visible before calculating
        return landmark["visibility"] >= self.min_visibility

    def get_shoulder_center(self, landmarks): #method to calculate shoulder's center
        if landmarks is None: #there is no body on the screen
            return None

        left = landmarks[LEFT_SHOULDER]
        right = landmarks[RIGHT_SHOULDER]

        if not self.is_landmark_visible(left) or not self.is_landmark_visible(right): #calling the method
            return None

        center_x = (left["x"] + right["x"]) / 2
        center_y = (left["y"] + right["y"]) / 2

        return (center_x, center_y)

    def get_hip_center(self, landmarks):
        if landmarks is None:
            return None

        left = landmarks[LEFT_HIP]
        right = landmarks[RIGHT_HIP]

        if not self.is_landmark_visible(left) or not self.is_landmark_visible(right):
            return None

        center_x = (left["x"] + right["x"]) / 2
        center_y = (left["y"] + right["y"]) / 2

        return (center_x, center_y)

    def extract_features(self, landmarks):
        if landmarks is None:
            return None

        nose = landmarks[NOSE]

        if not self.is_landmark_visible(nose):
            return None

        shoulder_center = self.get_shoulder_center(landmarks)
        hip_center = self.get_hip_center(landmarks)

        if shoulder_center is None or hip_center is None:
            return None

        return {
        "nose": (nose["x"], nose["y"]),
        "shoulder_center": shoulder_center,
        "hip_center": hip_center,
        "torso_height": hip_center[1] - shoulder_center[1]
        }

    def start_calibration(self): #reset the baseline to start freshly with new person  delete and start
        self.baseline = None
        self.calibration_samples = []
        self.is_calibrated = False
        self.is_calibrating = True #we are ready to accept new samples

    def _calculate_baseline(self): #the average of the 60 features,  started with_ means it is an inner method (Convention)
        samples = self.calibration_samples
        count = len(samples)

        baseline = {} 

        #EXAMPLE
        # {
        # "nose": (0.41, 0.21),
        # "shoulder_center": (0.41, 0.4033),
        # "hip_center": (0.46, 0.7033),
        # "torso_height": 0.30 it is not tuple
        # }

        for key in samples[0]:
            if isinstance(samples[0][key], tuple): #questioning is it tuple? 
                baseline[key] = (
                sum(sample[key][0] for sample in samples) / count, #calculating average of x ->0
                sum(sample[key][1] for sample in samples) / count #calculating average of y ->1
                )
            else: #if it is not tuple such as torso_height a single value
                baseline[key] = sum(
                sample[key] for sample in samples
                ) / count

        return baseline

    def calibrate(self, landmarks):
        if not self.is_calibrating:
            return False

        features = self.extract_features(landmarks)

        if features is None:
            return False

        self.calibration_samples.append(features)

        if len(self.calibration_samples) >= self.calibration_frames: 
            self.baseline = self._calculate_baseline()
            self.is_calibrating = False
            self.is_calibrated = True
            return True

        return False

    def reset_calibration(self): #delete and stop
        self.baseline = None
        self.calibration_samples = []
        self.is_calibrated = False
        self.is_calibrating = False

    def get_calibration_progress(self): #returns the number of samples we collected and how many left to complete calibration
        return len(self.calibration_samples), self.calibration_frames

    def get_movement(self, landmarks):
        if not self.is_calibrated: #make sure there is a baseline without it we can not compare
            return None

        features = self.extract_features(landmarks)

        if features is None:
            return None

        return {
        "hip_y": features["hip_center"][1] - self.baseline["hip_center"][1], 
        "shoulder_y": features["shoulder_center"][1] - self.baseline["shoulder_center"][1],
        "shoulder_x": features["shoulder_center"][0] - self.baseline["shoulder_center"][0],
        "hip_x": features["hip_center"][0] - self.baseline["hip_center"][0]
        }

    def detect_jump(self, movement):
        if movement is None:
            return False

        return (
            movement["hip_y"] < self.jump_threshold #if the value of hip_y is decreasing, means it is a jump for the shoulder and hip
            and
            movement["shoulder_y"] < self.jump_shoulder_threshold
        )


    def detect_slide(self, movement):
        if movement is None:
            return False

        return movement["shoulder_y"] > self.slide_threshold

    def detect_left(self, movement):
        if movement is None:
            return False

        return movement["shoulder_x"] < self.left_threshold


    def detect_right(self, movement):
        if movement is None:
            return False

        return movement["shoulder_x"] > self.right_threshold

    def get_action(self, movement): #turn movement into actions
        if movement is None:
            return "NONE"

        if self.detect_jump(movement):
            return "JUMP"

        if self.detect_slide(movement):
            return "SLIDE"

        if self.detect_left(movement):
            return "LEFT"

        if self.detect_right(movement):
            return "RIGHT"

        return "NONE"