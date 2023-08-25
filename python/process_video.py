'''
Driver used by dotnet program to process videos through and read license plates
when videos are uploaded to FTP server, triggered by Reolink's smart detection.
If license was deteced and read, saves and updates databases.
'''
import sys
import utils
from detect import VideoToLP, alpr_compalgv1, alpr_cp_default


class VideoProcessor(object):
    '''
    Process videos for license plates and update databases.

    Attributes
    ----------
    path : str
        the path of video to process (from the FTP server)
     
    alpr_alg : license plate detection algorithm
        see `detect.py`. default=alpr_compalgv1
        
    Methods
    -------
    process_video()
        Starts processing video
    '''
    def __init__(self, path):
        '''
        Arguments
        ----------
        path : str
            the path of video to process (from the FTP server)
        '''
        self.path = path
        self.alpr_alg = VideoToLP(path, alpr_alg=alpr_compalgv1)

    def process_video(self):
        '''
        Starts processing video
        
        Arguments
        ----------
        None
        
        Returns
        ----------
        "Complete" if success, else none
        '''
        # run video through detection algorithm
        detected_text, pred_metdata = self.alpr_alg.process_video()
        
        # store and update databases
        snapshot = pred_metdata['snapshot']
        utils.write_to_storage(detected_text, snapshot.screenshot, snapshot.lp_img)
        return "Complete"
    
        # error


if __name__ == "__main__":
    '''Driver for processing videos through LPRA and updating databases. 
    
    Arguments
    ----------
    path : str
        Path to video to process
    '''
    # read command line arguments for input video path
    args = sys.argv
    if len(args) > 1:
        fileinput = args
    else:
        raise '../samples/tlx.mp4'

    response = VideoProcessor(fileinput).process_video()
    print(response)