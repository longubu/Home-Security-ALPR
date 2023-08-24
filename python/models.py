'''Convenient models for storing data and predictions
'''


class LicensePlateData(object):
    '''Store license plate text'''
    def __init__(self, text):
        self.text = text

class SnapshotData(object):
    '''Stores a snapshot of the frame and license plate'''
    def __init__(self, screenshot, lp_img):
        self.screenshot = screenshot
        self.lp_img = lp_img

class Prediction:
    '''Stores prediction probability, label, and bounding box'''
    confidence: float
    label: str
    x_min: int
    y_min: int
    x_max: int
    y_max: int

    def __init__(self, dict) -> None:
        self.confidence = dict["confidence"]
        self.label = dict["label"]
        self.x_min = dict["x_min"]
        self.y_min = dict["y_min"]
        self.x_max = dict["x_max"]
        self.y_max = dict["y_max"]