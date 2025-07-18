import sounddevice as sd

from . import audio as audio


class MicManager:
    def __init__(self):
        self.stream = None

    def start(self, callback):
        self.stop()
        self.stream = sd.InputStream(
            samplerate=audio.MIC_RATE,
            device=audio.MIC_DEVICE_INDEX,
            channels=audio.MIC_CHANNELS,
            dtype='int16',
            blocksize=audio.CHUNK_SIZE,
            callback=callback,
        )
        self.stream.start()

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"⚠️ Error closing mic stream: {e}")
            self.stream = None
