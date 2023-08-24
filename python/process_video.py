'''
Driver used by dotnet program to process videos through the license plate reader algorithm (LPRA)
If successful, saves and updates database with license plate and event.
'''
import utils
from lpra import SimpleLPReader, CodeProject_ALPR


class VideoProcessor(object):
    '''
    Used to process videos for license plates and update databases.

    Attributes
    ----------
    path : str
        the path of video to process (from the FTP server)
     
    lpra_alg : License Plate Reader Algorithm class
        stored to debug algorithm predictions. see `lpra.py`
        
    Methods
    -------
    process_video()
        Starts processing video through LPRA and updates databases
    '''
    def __init__(self, path):
        '''
        Parameters
        ----------
        name : str
            The name of the animal
        sound : str
            The sound the animal makes
        num_legs : int, optional
            The number of legs the animal (default is 4)
        '''
        self.path = path
        self.lpra_alg = SimpleLPReader(self.path)
        
    def process_video(self):
        plate_txt, lpra_metdata = self.lpra_alg.process_video()
        snapshot_data = lpra_metdata['snapshot']
        utils.write_to_storage(plate_txt, snapshot_data.screenshot, snapshot_data.lp_img)
        return "Complete"
        # error


if __name__ == "__main__":
    '''Driver for processing videos through LPRA and updating databases. 
    
    Arguments
    ----------
    path : str
        Path to video to process
    '''
    import sys
    args = sys.argv
    if len(args) > 1:
        fileinput = args
    else:
        raise RuntimeError('Please specify path to video file')

    response = VideoProcessor(fileinput).process_video()
    print(response)