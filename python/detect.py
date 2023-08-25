'''
Algorithms to detect and read license plates
'''
import os
import cv2
import requests
from models import Prediction, SnapshotData

# Codeproject.AI ML server and module paths
base_url = "http://localhost:32168/v1/{path}"  

apiserver = {
    'obj_detection': base_url.format(path="vision/detection"),
    'alpr': base_url.format(path="image/alpr"),  # doesn't work well
    'custom_license_plate': base_url.format(path="vision/custom/license-plate"),
    'ocr': base_url.format(path='image/ocr')
}

predictions_key = 'predictions'


def valid_plate(val: str):
    '''Rules to check for valid plates'''
    if not val:
        return False

    if (len(val)) >= 8 or len(val) <= 5:
        return False

    return True


def detect_cars(image_bytes):
    '''Detect cars from image_bytes usin Codeproject.AI general object detection module'''
    # send image to codeproject AI module
    obj_response = requests.post(apiserver['obj_detection'],
                                 files={"image": image_bytes}).json()

    # loop through response and find car predictions
    preds = []
    for object_pred_resp in obj_response.get(predictions_key, []):
        object_prediction = Prediction(object_pred_resp)

        if object_prediction.confidence > 0.80 and object_prediction.label == 'car':
            preds.append(object_prediction)

    return preds


def detect_licenseplates(image_bytes):
    '''Detect licenseplates from image_bytes using Codeproject.AI custom license plate module'''
    # send image to codeproject AI module
    license_response = requests.post(apiserver['custom_license_plate'],
                                     files={"image": image_bytes}).json()

    # loop through response and store predictions
    preds = []
    for lic_obj in license_response.get(predictions_key, []):
        license_prediction = Prediction(lic_obj)
        preds.append(license_prediction)

    return preds
    

def read_licenseplate(image_bytes):
    '''Read license plates from image_bytes using Codeproject.AI OCR module'''
    # send image to codeproject AI modules
    ocr_response = requests.post(apiserver['ocr'],
                                 files={"image": image_bytes}).json()    

    # loop through responses and store predictions
    preds = []
    for ocr_obj in ocr_response.get(predictions_key, []):
        ocr_prediction = Prediction(ocr_obj)
        detected_text = ocr_prediction.label
        
        # only get valid license text, ignore all others (plate frame text)
        if not valid_plate(detected_text): 
            continue

        preds.append(ocr_prediction)

    return preds
    

def alpr_cp_default(frame):
    '''Read license plate from image/screenshot using default codeproject AI's ALPR module'''
    # convert to bytes to send over HTTP for codeproject.AI
    image_bytes = cv2.imencode('.jpg', frame)[1].tobytes()
    
    # first, detect if car is present using general object detection
    obj_response = requests.post(apiserver['alpr'],
                                 files={"image": image_bytes}).json()

    # loop through all objects detected and find all cars, if any
    preds = []
    for object_pred_resp in obj_response.get(predictions_key, []):
        lp_prediction = Prediction(object_pred_resp)
        
        # remove default text output of model
        lp_prediction.label = lp_prediction.label.replace('Plate: ', '') 
        
        # # crop for license plate only
        # cropped_image = frame[lp_prediction.y_min:lp_prediction.y_max,
        #                       lp_prediction.x_min:lp_prediction.x_max]
        
        if not valid_plate(lp_prediction.label):  # no more than 7 characters
            continue
        
        preds.append(lp_prediction)

    return preds


def alpr_compalgv1(frame):
    '''Read license plate from image/screenshot using a sequence of codeproject AI's modules'''
    preds = []
    
    # convert to bytes to send to Codeproject.AI APIs
    image_bytes = cv2.imencode('.jpg', frame)[1].tobytes()

    # First, detect all cars present using general object detection
    # - there can be multiple cars/lps in same frame
    car_predictions = detect_cars(image_bytes)
    if not car_predictions:
        return preds

    # Next, find all license plates  using custom/lp module
    license_predictions = detect_licenseplates(image_bytes)

    # for all license plates found, crop to that license and
    # read all text using OCR, only save valid license plate texts (<7 characters)
    for license_pred in license_predictions:
        cropped_image = frame[license_pred.y_min:license_pred.y_max,
                              license_pred.x_min:license_pred.x_max]
        cropped_bytes = cv2.imencode('.jpg', cropped_image)[1].tobytes()

        valid_lp_preds = read_licenseplate(cropped_bytes)
        
        # use correct license plate bounding box, not zoomed OCR detection
        for valid_lp_pred in valid_lp_preds:
            valid_lp_pred.x_min = license_pred.x_min
            valid_lp_pred.x_max = license_pred.x_max
            valid_lp_pred.y_min = license_pred.y_min
            valid_lp_pred.y_max = license_pred.y_max

        preds.extend(valid_lp_preds)
        
    return preds


class VideoToLP(object):
    '''
    Detects and reads license plate from video. Detects and read
    licenese plate from each frame and selects the plate with the most 
    occurence.
    
    Attributes
    ----------
    path : str
        the path of video to process (from the FTP server)
     
    alpr_alg : license plate detection algorithm
        choices are `alpr_compalgv1` or `alpr_cp_default`
        
    Methods
    -------
    process_video()
        Starts processing video
    '''
    def __init__(self, path, alpr_alg=alpr_compalgv1):
        '''
        Arguments
        ----------
        path: the path of video to process
        
        alpr_alg : license plate detection algorithm
            choices are `alpr_compalgv1` or `alpr_cp_default`
        '''
        if not os.path.exists(path):
            raise RuntimeError('%s does not exist' % path)
            
        self.path = path
        self.alpr_alg = alpr_alg

        # set initial values
        self.occurrence = {}
        
    def process_video(self):
        '''
        Starts processing video
        
        Arguments
        ----------
        None
        
        Returns
        ----------
        plate_txt: str
            string of license plate text detected
        
        pred_metadata: dict
            metadata from prediction algorithm for debugging
        '''
        # open video using cv2
        cap = cv2.VideoCapture(self.path)
        print("Starting video capture ", self.path)
        
        # detect & read license plate for each frame
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            frame_count += 1
            
            if not ret:
                print("no frame to capture")
                break
    
            # read every 3 frames to save time
            if frame_count % 3 != 0:
                continue
            
            # if frame_count % 24 == 0 :
            #     print('... frame: %i' % frame_count)
            
            preds = self.alpr_alg(frame)
            for pred in preds:
                detected_text = pred.label
                cropped_image = frame[pred.y_min:pred.y_max, 
                                      pred.x_min:pred.x_max]
                
                if detected_text not in self.occurrence:
                    self.occurrence[detected_text] = {
                            'text': detected_text,
                            'count': 1,
                            'snapshot': SnapshotData(frame, cropped_image),  # store image of car & license plate for reference
                        }
                else:
                    self.occurrence[detected_text]['count'] += 1
                    
            # end process frame
        
        # end video processing
        cap.release()
        cv2.destroyAllWindows()
        
        # if no license plates were read, return error
        if len(self.occurrence) == 0:
            print("error occurrence is empty")
            return "", {}
        
        # return most frequent LP text read
        sorted_occurrence = sorted(self.occurrence.items(), key=lambda x: x[1]['count'], reverse=True)
        plate_txt, pred_metadata = next(iter(sorted_occurrence))
        print('ACTUAL PLATE {}'.format(plate_txt))
        return plate_txt, pred_metadata
    
if __name__ == "__main__":
    imageinput = r"../samples/tlx_snapshot.png"
    videoinput = r"../samples/tlx.mp4"

    print("Testing ALPR on frame snapshot: %s" % imageinput)
    frame = cv2.imread(imageinput)
    ret = alpr_compalgv1(frame)
    print(ret)
    
    print("using default ALPR: Testing ALPR on video: %s" % videoinput)
    video_alpr = VideoToLP(videoinput, alpr_alg=alpr_cp_default)
    ret2 = video_alpr.process_video()
    print(ret2)
    
    print("using compalgv1: Testing ALPR on video: %s" % videoinput)
    video_alpr = VideoToLP(videoinput, alpr_alg=alpr_compalgv1)
    ret2 = video_alpr.process_video()
    print(ret2)
    print('---')
    print('All Done')