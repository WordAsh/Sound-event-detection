'''
demo for test

'''
import sys
import datetime
import time
import os
from dataclasses import dataclass
from typing import Optional
import queue
import torch
from omegaconf import OmegaConf
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from sed_demo.audio_manager import Audio
from sed_demo import AUDIOSET_LABELS_PATH
from sed_demo.utils import load_csv_labels
from sed_demo.models import Cnn9_GMP_64x64
from sed_demo.audio_loop import AsynchAudioInputStream
from sed_demo.audio_loop import AsynchWavAudioInputStream
from sed_demo.inference import AudioModelInference, PredictionTracker

class SEDApp():
    '''
    This class emulates the procedure of sound event detection and send messages out.

    1. Instantiate an "AsynchAudioInputStream" to write an audio ring buffer from the microphone.
    2. Instantiate a "Cnn9_GMP_64x64" to detect categories from audio
    3. Instantiate an "AudioModelInference" that uses the CNN to periodically detect categories from the ring buffer.
    4. Instantiate a "PredictionTracker" to filter out undesired categories from the CNN output and return the top K, sorted by confidence.
    '''

    def __init__(
            self,
            model_path,
            file_name,
            all_labels, tracked_labels=None,
            samplerate=32000, audio_chunk_length=1024, ringbuffer_length=40000,
            model_winsize=1024, stft_hopsize=512, stft_window="hann",
            n_mels=64, mel_fmin=50, mel_fmax=14000,
            top_k=5):
        """
        :param all_labels: list of categories in same quantity and
            order as used during model training. See files in the ``assets`` dir.
        :param tracked_labels: optionally, a subset of ``all_labels``
            specifying the labels to track (rest will be ignored).
        :param samplerate: Audio samplerate. Ideally it should match the one
            used during model training.
        :param audio_chunk_length: number of samples that the audio recording
            will write at once. Not relevant for the model, but larger chunks
            impose larger delays for the real-time system.
        :param ringbuffer_length: The recorder will continuously update a ring
            buffer. To perform inference, the model will read the whole ring
            buffer, therefore this length determines the duration of the model
            input. E.g. ``length=samplerate`` corresponds to 1 second. Too short
            lengths may miss some contents, too large lengths may take too long
            for real-time computations.
        :param model_winsize: We have waveforms, but the model expects
            a time-frequency representation (log mel spectrogram). This is the
            window size for the STFT and mel operations. Should match training
            settings.
        :param n_mels: Number of mel bins. Should match training settings.
        :param mel_fmin: Lowest mel bin. Should match training settings.
        :param mel_fmax: Highest mel bin. Should match training settings.
        :param top_k: For each prediction, the app will show only the ``top_k``
            categories with highest confidence, in descending order.
        """
        # 1. Input stream from microphone
        # self.audiostream = AsynchAudioInputStream(
        #     samplerate, audio_chunk_length, ringbuffer_length)

        self.file_name = file_name
        self.audiostream = AsynchWavAudioInputStream(self.file_name,samplerate, audio_chunk_length,ringbuffer_length)

        # 2. DL pretrained model to predict tags from ring buffer
        num_audioset_classes = len(all_labels)
        self.model = Cnn9_GMP_64x64(num_audioset_classes)
        checkpoint = torch.load(model_path,
                                map_location=lambda storage, loc: storage)
        self.model.load_state_dict(checkpoint["model"])
        # 3. Inference: periodically read the input stream with the model
        self.inference = AudioModelInference(
            self.model, model_winsize, stft_hopsize, samplerate, stft_window,
            n_mels, mel_fmin, mel_fmax)
        # 4. Tracker: process predictions, return the top K among allowed ones
        self.tracker = PredictionTracker(all_labels, allow_list=tracked_labels)
        #
        self.top_k = top_k
        self.thread = None


    def inference_loop(self):
        """
        This method is intended to run asynchronously, i.e. in a separate
        thread.It loops indefinitely, performing
        """
        dl_inference = self.inference(self.audiostream.read())
        top_preds = self.tracker(dl_inference, self.top_k)
        for clsname, _ in top_preds:
            return clsname

    def stop(self):
        """
        Stops the ring buffer recording (the inference loop stops as well)
        when user presses stop button.
        """
        # Note that the superclass already handles the update of the
        # ``is_running()`` method, so the thread will stop based on that.
        # Here we only need to stop the audio stream.
        self.audiostream.stop()
        self.audiostream.terminate()


# ##############################################################################
# # OMEGACONF
# ##############################################################################
@dataclass
class ConfDef:
    """
    Check ``SEDApp`` docstring for details on the parameters. Defaults should
    work reasonably well out of the box.
    """
    FILE_NAME: Optional[str] = None
    ALL_LABELS_PATH: str = AUDIOSET_LABELS_PATH
    SUBSET_LABELS_PATH: Optional[str] = None
    MODEL_PATH: str = os.path.join(
        "models", "Cnn9_GMP_64x64_300000_iterations_mAP=0.37.pth")
    #
    SAMPLERATE: int = 32000
    AUDIO_CHUNK_LENGTH: int = 1024
    RINGBUFFER_LENGTH: int = int(32000 * 3)
    #
    MODEL_WINSIZE: int = 1024
    STFT_HOPSIZE: int = 512
    STFT_WINDOW: str = "hann"
    N_MELS: int = 64
    MEL_FMIN: int = 50
    MEL_FMAX: int = 14000
    # frontend
    TOP_K: int = 6


# #####################################################################
# # WATCH FILE CHANGED
# #####################################################################
class WatcherHandler(FileSystemEventHandler):
    def __init__(self):
        FileSystemEventHandler.__init__(self)

    def on_created(self,event):
        if not event.is_directory:  #ignore file folder
            file_name = os.path.basename(event.src_path)
            file_queue.put(file_name)

def start_monitoring(path_tp_watch):
    event_handler = WatcherHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path_tp_watch, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ##############################################################################
# # MAIN ROUTINE
# ##############################################################################
if __name__ == '__main__':
    time_span = 10 #unit in seconds
    detect_results = {}  #save every second detect result

    file_queue = queue.Queue()
    folder_to_watch = "/home/rigon/Projects/SoundEventDetection/General-Purpose-Sound-Recognition-Demo/wav_files/"

    monitoring_threading = threading.Thread(target=start_monitoring, args=(folder_to_watch,),  daemon=True)
    monitoring_threading.start()

    CONF = OmegaConf.structured(ConfDef())
    cli_conf = OmegaConf.from_cli()
    CONF = OmegaConf.merge(CONF, cli_conf)
    # print("\n\nCONFIGURATION:")
    # print(OmegaConf.to_yaml(CONF), end="\n\n\n")

    _, _, all_labels = load_csv_labels(CONF.ALL_LABELS_PATH)
    if CONF.SUBSET_LABELS_PATH is None:
        subset_labels = None
    else:
        _, _, subset_labels = load_csv_labels(CONF.SUBSET_LABELS_PATH)

    while(True):
        file_name = file_queue.get()
        if file_name is not None:
            app = SEDApp(
                CONF.MODEL_PATH,
                file_name,
                all_labels, subset_labels,
                CONF.SAMPLERATE, CONF.AUDIO_CHUNK_LENGTH, CONF.RINGBUFFER_LENGTH,
                CONF.MODEL_WINSIZE, CONF.STFT_HOPSIZE, CONF.STFT_WINDOW,
                CONF.N_MELS, CONF.MEL_FMIN, CONF.MEL_FMAX,
                CONF.TOP_K)
            app.audiostream.start()

            endTime = datetime.datetime.now() + datetime.timedelta(seconds=time_span)  #time span
            while(True):
                clsname = app.inference_loop()
                occur_time = time.strftime(" %Y-%m-%d %H:%M:%S",time.localtime())
                time.sleep(1)     #delay for 1 sec

                if clsname in detect_results:
                    detect_results[clsname] += 1
                else:
                    detect_results[clsname] = 1

                #print(clsname,occur_time)
                if (endTime - datetime.datetime.now()).seconds == 0:
                    app.stop()
                    print("Detection finished!")
                    break

            top_result = max(detect_results, key=detect_results.get)  
            print(top_result)
            file_queue.task_done()


#region Record sound
    # audio_manager = Audio(time_span)
    # audio_manager.record()
#endregion