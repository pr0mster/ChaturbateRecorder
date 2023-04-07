import threading
import time

from model import Model
from postprocessing import PostProcessing
import config


settings = config.readConfig()

class Monitor(threading.Thread):
    def __init__(self, wishlist):
        threading.Thread.__init__(self, daemon=True)
        self.lock = threading.Lock()

        self.wishlist = wishlist
        self.monitoring_threads = {}
        self.recording_threads = {}
        self.done = []

        self.postprocess = None
        if settings['postProcessingCommand']:
            self.postprocess = PostProcessing(settings['postProcessingCommand'], settings['postProcessingThreads'] or 2)

    def isHandled(self, model):
        return self.isMonitored(model) or self.isRecording(model)
    
    def isMonitored(self, model):
        return model in (model for model in self.monitoring_threads.keys())
    
    def isRecording(self, model):
        return model in (model for model in self.recording_threads.keys())

    def startRecording(self, modelThread):
        self.lock.acquire()
        self.recording_threads[modelThread.model] = modelThread
        del self.monitoring_threads[modelThread.model]
        self.lock.release()
    
    def stopRecording(self, modelThread):
        self.lock.acquire()
        self.monitoring_threads[modelThread.model] = modelThread
        del self.recording_threads[modelThread.model]
        self.lock.release()

        self.processRecording(modelThread.model, modelThread.file, modelThread.info()['duration'])
        
    def processRecording(self, model, file, duration):
        if self.postprocess:
            self.postprocess.add({'model': model, 'path': file})
        self.done.append({'path': file, 'duration': duration})

    def stopMonitoring(self, model):
        self.lock.acquire()
        self.monitoring_threads[model].running = False
        self.monitoring_threads[model].join()
        del self.monitoring_threads[model]
        self.lock.release()

    def startMonitoring(self, model):
        thread = Model(model, self)
        thread.daemon = True
        thread.start()

        self.lock.acquire()
        self.monitoring_threads[model] = thread
        self.lock.release()

    def cleanThreads(self):
        self.lock.acquire()
        models = list(self.recording_threads.keys())
        self.lock.release()

        for model in models:
            if model not in self.wishlist.wishlist:
                self.recording_threads[model].stopRecording()
                self.stopMonitoring(model)
        
        # models = self.recording_threads.keys()
        # for model in models:
        #     if not self.recording_threads[model].is_alive():
        #         self.recording_threads[model].stopRecording()
            
        # models = self.monitoring_threads.keys()
        # for model in models:
        #     if not self.monitoring_threads[model].is_alive():
        #         self.stopMonitoring(model)
        

    def loop(self):
        # Kill off stopped threads (will be recreated in the next step if needed)
        self.cleanThreads()
        
        # Start a thread for each model in our wishlist
        for model in self.wishlist.wishlist:
            if not self.isHandled(model):
                self.startMonitoring(model)

    def run(self):
        while True:
            self.loop()
            time.sleep(1)