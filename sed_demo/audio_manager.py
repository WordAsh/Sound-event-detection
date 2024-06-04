import pyaudio
import wave
import os
from datetime import datetime



class Audio:
    def __init__(self,record_time : int):
        '''
        :param int record_time: record time length in seconds
        '''
        self.CHUNK = 1024
        self.CHANNELS = 2
        
        #human listen
        self.FORMAT = pyaudio.paInt16
        self.RATE = 44100

        #machine listen
        # self.FORMAT = pyaudio.paFloat32
        # self.RATE = 32000
        
        self.RECORD_SECONDS = record_time
        self.WAVE_OUTPUT_FILENAME = os.path.join(os.path.abspath('.'), f"wav_files/{datetime.now().replace(microsecond=0)}.wav")

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=self.FORMAT,
                        channels=self.CHANNELS,
                        rate=self.RATE,
                        input=True,
                        frames_per_buffer=self.CHUNK)

    def save(self, filename, data):
        '''
        write into .wav file
        '''
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(data)
        wf.close()

    def record(self):
        '''
        record sound using microphone and save .wav file
        '''
        frames = []
        for i in range(0, int(self.RATE / self.CHUNK * self.RECORD_SECONDS)):
            data = self.stream.read(self.CHUNK)
            frames.append(data)

        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

        data = b''.join(frames)
        self.save(self.WAVE_OUTPUT_FILENAME, data)


    def play(self):
        '''
        play the .wav file saved locally
        '''
        wf = wave.open(os.path.join(os.path.abspath('.'), "wav_files/esp32.wav"),'rb')
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),channels=wf.getnchannels(),rate=wf.getframerate(),output=True)

        data = wf.readframes(self.CHUNK)
        while data != b'':
            stream.write(data)
            data = wf.readframes(self.CHUNK)

        stream.stop_stream()
        stream.close()
        p.terminate()

