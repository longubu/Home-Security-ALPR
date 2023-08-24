'''General utility functions'''
import os
import cv2
from datetime import datetime
from models import LicensePlateData
import data_repo


def get_rtsp_url(stream, quality):
    '''Get RTSP url for Reolink NVR camera.'''
    uname = os.getenv('RTSP_USER')
    password = os.environ.get('RTSP_PASSWORD')
    camera_url = os.environ.get('CAM_01_FEED')
    return "rtsp://{uname}:{password}@{nvrip}/h264Preview_{stream}_{quality}".format(uname=uname, password=password,
                                                                                     nvrip=camera_url, stream=stream,
                                                                                     quality=quality)


def cv_resize(img, scale=0.5):
    '''Resize length/width of cv image by scale'''
    return cv2.resize(img, (0, 0), fx=scale, fy=scale)


def cv_enlarge(img, scale_percent=200):
    '''Enlarge (upscale) img by scale_percent'''
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    dim = (width, height)
    return cv2.resize(img, dim, interpolation=cv2.INTER_AREA)


def create_dir_helper(directory_path):
    '''Create directory and sub-directories if not exist'''
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def write_to_storage(plate, frame, plate_only_img):
    '''Write screenshot of frame/license plate to local directory.
    Update database of new license plates and car-detected events
    
    Arguments
    ----------
    plate: str
        License plate string
    
    frame: cv image
        Screenshot of camera video containing car/license plate
    
    plate_only_img: cv image
        Cropped image containing only license plate
    
    Returns
    ----------
    response: str
        "Success" or "Failure"
    '''
    
    output_directory_fmt = "C:\\EagleEyeProject\\license_plates\\{plate}"
    datestamp = datetime.now().strftime("%Y-%m-%d %H %M %S")

    output_dir = output_directory_fmt.format(plate=plate)
    create_dir_helper(output_dir)

    # plate_path = os.path.join(output_dir, plate)
    # utils.create_dir_helper(plate_path)

    screenshot_path = os.path.join(output_dir, "{}.jpg".format(datestamp))

    # ss_plate = os.path.join(output_dir, "{}_plate.jpg".format(date))

    print('Writing to: ', screenshot_path)

    cv2.imwrite(screenshot_path, frame)
    # cv2.imwrite(ss_plate, plate_only_img)

    # retval, plate_bytes = cv2.imencode('.jpg', plate_only_img)
    # car_bytes = cv2.imencode('.jpg', frame)

    json_resp = LicensePlateData(plate)

    data_repo.db_upsert(json_resp)

    return "Success"