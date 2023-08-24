'''
License Plate Reader Algorithms (LPRA)

Algorithms
----------
    simple_lpreader_v1: currently used algorithm using a sequence of detection modules
    
    codeproject_alpr: out-of-the-box license plate reader from codeproject.AI; not used, too many false positives
'''
import cv2
import requests
from adhoc_rules import words_to_ignore
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
    if not val:
        return False

    if (len(val)) > 7:  # can't be greater > 7 characters
        return False

    if val.lower() in words_to_ignore:
        return False

    return True


class SimpleLPReader(object):
    '''
    Attributes
    ----------
    cap : cv2 VideoCapture object 
        video opened using openCV's VideoCapture object, sequence of frames
    occurence : dict
        used to track occurrence of each text read through frames
    total_detection : int
        track how often license plates and text were successfully processed
    frame_count : int
        track frames processed so far
        
    Methods
    -------
    read_lp(???)
        Detects and reads license plates. Returns ?
    
    '''
    def __init__(self, path):
        '''
        Arguments
        ----------
        path: the path of video to process
        '''
        self.path = path
        
        # set initial values
        self.occurrence = {}

    def process_video(self):
        '''
        Detect & read license plate from video.
        
        Parameters
        ----------
        None
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
    
            # read every 3 frames to save time, camera FPS=24
            if frame_count % 3 != 0:
                continue
            
            # convert to bytes to send over HTTP for codeproject.AI
            if frame_count % 24 == 0 :
                print('... frame: %i' % frame_count)
            
            image_bytes = cv2.imencode('.jpg', frame)[1].tobytes()
            
            # First, detect car is present using general object detection
            car_found, car_predictions = self.detect_cars(image_bytes)
            if not car_found:
                continue
        
            # Find all license plates (in case there are multiple cars in same frame) using custom/lp module
            license_found, license_predictions = self.detect_licenseplates(image_bytes)
            
            # for all license plates found, crop to that license and
            # read all text using OCR, only save valid license plate texts (7 characters)
            for license_pred in license_predictions:
                cropped_image = frame[license_pred.y_min:license_pred.y_max,
                                      license_pred.x_min:license_pred.x_max]
                cropped_bytes = cv2.imencode('.jpg', cropped_image)[1].tobytes()

                valid_lp_text_found, valid_lp_preds = self.read_licenseplate(cropped_bytes)
                
                if not valid_lp_text_found:
                    continue
                
                # count all valid license plates texts read and keep track
                for valid_lp_pred in valid_lp_preds:
                    detected_text = valid_lp_pred.label
                    if detected_text not in self.occurrence:
                        self.occurrence[detected_text] = {
                            'text': detected_text,
                            'count': 1,
                            'snapshot': SnapshotData(frame, cropped_image),  # store car & license plate for reference
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
            return "Error"
        
        # return most frequent LP text read
        sorted_occurrence = sorted(self.occurrence.items(), key=lambda x: x[1]['count'], reverse=True)
        plate_txt, lpra_metadata = next(iter(sorted_occurrence))
        print('ACTUAL PLATE {}'.format(plate_txt))
        return plate_txt, lpra_metadata
    
        # utils.write_to_storage(first_item[0], self.response_data.screenshot, self.response_data.lp_img)
        # return "Complete"
            
    def detect_cars(self, image_bytes):
        # first, detect if car is present using general object detection
        obj_response = requests.post(apiserver['obj_detection'],
                                     files={"image": image_bytes}).json()

        # no objects found, skip
        if predictions_key not in obj_response:
            return False, []
     
        # loop through all objects detected and find all cars, if any
        car_found = False
        car_predictions = []
        for object_pred_resp in obj_response["predictions"]:
            object_prediction = Prediction(object_pred_resp)
            
            if object_prediction.confidence > 0.80 and object_prediction.label == 'car':
                car_found = True
                car_predictions.append(object_prediction)
            
        return car_found, car_predictions
    
    def detect_licenseplates(self, image_bytes):
        license_response = requests.post(apiserver['custom_license_plate'],
                                         files={"image": image_bytes}).json()
            
        # no license plate found, skip
        if predictions_key not in license_response:
            return False, []
        
        license_found = True  # since a valid response was returned
        license_predictions = []
        for lic_obj in license_response[predictions_key]:
            license_prediction = Prediction(lic_obj)
            license_predictions.append(license_prediction)
            
        return license_found, license_predictions

    def read_licenseplate(self, image_bytes):
        ocr_response = requests.post(apiserver['ocr'],
                                     files={"image": image_bytes}).json()    
    
        if predictions_key not in ocr_response:
            return False, []
    
        valid_lp_text_found = False
        valid_lp_preds = []
        for ocr_obj in ocr_response[predictions_key]:
            ocr_prediction = Prediction(ocr_obj)
            detected_text = ocr_prediction.label
                    
            if not valid_plate(detected_text):  # only 7 characters
                continue
            
            valid_lp_preds.append(ocr_prediction)
            valid_lp_text_found = True
            
        return valid_lp_text_found, valid_lp_preds
    
    
class CodeProject_ALPR(object):
    def __init__(self, path):
        '''
        Arguments
        ----------
        path: the path of video to process
        '''
        self.path = path
        
        # set initial values
        self.occurrence = {}
      
    def process_video(self):
        '''
        Detect & read license plate from video.
        
        Parameters
        ----------
        None
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
    
            # read every N frames to save resources
            if frame_count % 3 != 0:
                continue
            
            # convert to bytes to send over HTTP for codeproject.AI
            image_bytes = cv2.imencode('.jpg', frame)[1].tobytes()
            
            # first, detect if car is present using general object detection
            obj_response = requests.post(apiserver['alpr'],
                                         files={"image": image_bytes}).json()
    
            # no objects found, skip
            if predictions_key not in obj_response:
                return False, []
         
            # loop through all objects detected and find all cars, if any
            for object_pred_resp in obj_response["predictions"]:
                lp_prediction = Prediction(object_pred_resp)
                detected_text = lp_prediction.label
                
                # remove default text output of model
                detected_text = detected_text.replace('Plate: ', '') 
                
                # crop for license plate only
                cropped_image = frame[lp_prediction.y_min:lp_prediction.y_max,
                                      lp_prediction.x_min:lp_prediction.x_max]
                
                if not valid_plate(detected_text):  # no more than 7 characters
                    continue
                
                if detected_text not in self.occurrence:
                    self.occurrence[detected_text] = {
                        'text': detected_text,
                        'count': 1,
                        'snapshot': SnapshotData(frame, cropped_image),  # store car & license plate for reference
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
            return "Error"
        
        # return most frequent LP text read
        sorted_occurrence = sorted(self.occurrence.items(), key=lambda x: x[1]['count'], reverse=True)
        plate_txt, lpra_metadata = next(iter(sorted_occurrence))
        print('ACTUAL PLATE {}'.format(plate_txt))
        return plate_txt, lpra_metadata
    
if __name__ == "__main__":

    fileinput = r"C:\Users\Lbot3000\Desktop\tlx.mp4"
    
    alg = SimpleLPReader(fileinput)
    # alg = CodeProject_ALPR(fileinput)
    ret = alg.process_video()
    