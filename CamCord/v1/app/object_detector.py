import cv2
import numpy as np
import os
from .config import settings # For consistency, though not directly used by paths here

# Define paths to model files relative to the 'app' directory or a known base
# Assuming 'CamCord/v1/app/' is the execution context or models are placed there.
APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(APP_DIR, "models")

CFG_PATH = os.path.join(MODELS_DIR, "yolov4-tiny.cfg")
WEIGHTS_PATH = os.path.join(MODELS_DIR, "yolov4-tiny.weights")
CLASSES_PATH = os.path.join(MODELS_DIR, "coco.names")


class ObjectDetector:
    def __init__(self, cfg_path=CFG_PATH, weights_path=WEIGHTS_PATH, classes_path=CLASSES_PATH, confidence_threshold=0.5, nms_threshold=0.4):
        self.net = None
        self.classes = []
        self.output_layers = []
        self.layer_names = []
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold

        try:
            if not os.path.exists(cfg_path):
                print(f"[ObjectDetector] Error: Config file not found at {cfg_path}")
                return
            if not os.path.exists(weights_path):
                print(f"[ObjectDetector] Error: Weights file not found at {weights_path}")
                return
            if not os.path.exists(classes_path):
                print(f"[ObjectDetector] Error: Classes file not found at {classes_path}")
                return

            self.net = cv2.dnn.readNetFromDarknet(cfg_path, weights_path)
            # Try to use CUDA if available
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                print("[ObjectDetector] Set DNN backend to CUDA")
            else:
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                print("[ObjectDetector] Set DNN backend to OpenCV (CPU)")

            self.layer_names = self.net.getLayerNames()
            # Compatibility for different OpenCV versions for getUnconnectedOutLayers()
            try:
                # For OpenCV >= 4.x
                self.output_layers = [self.layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
            except TypeError: # OpenCV 3.x and some 4.x versions might return a 2D array
                 self.output_layers = [self.layer_names[i[0] - 1] for i in self.net.getUnconnectedOutLayers()]


            with open(classes_path, 'r') as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            print(f"[ObjectDetector] Initialized successfully with {len(self.classes)} classes.")

        except Exception as e:
            print(f"[ObjectDetector] Error during initialization: {e}")
            self.net = None # Ensure net is None if init fails

    def detect(self, frame):
        if self.net is None:
            # print("[ObjectDetector] Network not initialized. Cannot detect.")
            return [], frame # Return empty list and original frame

        height, width = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        
        try:
            layer_outputs = self.net.forward(self.output_layers)
        except Exception as e:
            print(f"[ObjectDetector] Error during forward pass: {e}")
            return [], frame


        boxes = []
        confidences = []
        class_ids = []
        detections_info = []

        for output in layer_outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > self.confidence_threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, self.nms_threshold)

        frame_with_overlays = frame.copy() # Make a copy to draw on

        if len(indexes) > 0:
            # Ensure indexes is iterable and handle the case where it might be a scalar if only one detection
            # For OpenCV, NMSBoxes typically returns a 2D array (even if one row) or an empty tuple.
            # Flattening handles the 2D array case.
            for i in indexes.flatten():
                x, y, w, h = boxes[i]
                label = str(self.classes[class_ids[i]])
                confidence = confidences[i]
                color = (0, 255, 0) # Green for bounding box
                cv2.rectangle(frame_with_overlays, (x, y), (x + w, y + h), color, 2)
                text = f"{label}: {confidence:.2f}"
                cv2.putText(frame_with_overlays, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                detections_info.append({"label": label, "confidence": confidence, "box": [x, y, w, h]})
        
        return detections_info, frame_with_overlays

# Example Usage (for testing if run directly, not part of the module's API)
if __name__ == '__main__':
    # This part will only run if object_detector.py is executed directly.
    # It requires model files to be present at the defined paths.
    print("Object Detector direct execution test.")
    print(f"Looking for models in: {MODELS_DIR}")
    print(f"CFG_PATH: {CFG_PATH}")
    print(f"WEIGHTS_PATH: {WEIGHTS_PATH}")
    print(f"CLASSES_PATH: {CLASSES_PATH}")

    # Check if model files exist for the test
    if not all(os.path.exists(p) for p in [CFG_PATH, WEIGHTS_PATH, CLASSES_PATH]):
        print("Test requires model files (yolov4-tiny.cfg, yolov4-tiny.weights, coco.names) in the models directory.")
        print("Please download them or ensure paths are correct.")
        # A quick way to inform user how to get them:
        print("\nExample: Download yolov4-tiny.weights from https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_tiny/yolov4-tiny.weights")
        print("Download yolov4-tiny.cfg from https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg")
        print("Download coco.names from https://raw.githubusercontent.com/AlexeyAB/darknet/master/data/coco.names")
        print(f"And place them into {MODELS_DIR}\n")
    else:
        detector = ObjectDetector()
        if detector.net:
            # Create a dummy black image for testing
            dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(dummy_frame, "Test Image", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            detections, frame_with_overlays = detector.detect(dummy_frame)
            
            print(f"Detections: {detections}")
            # To display the image if in a GUI environment (won't work in non-GUI sandbox)
            # cv2.imshow("Detections", frame_with_overlays)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()
            print("Test detection run. If no errors and Detections list is printed, basic functionality is okay.")
        else:
            print("Detector network not initialized. Test cannot run.")

print(f"[ObjectDetector Module] Loaded. Model paths set relative to: {APP_DIR}")
