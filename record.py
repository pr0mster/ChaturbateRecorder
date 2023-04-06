import time
import os
import threading

from model import Model
import config
from postprocessing import PostProcessing

# Enable ANSI escape sequence processing in Windows
if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

settings = {}

threads = []
recording_threads = []

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')



class CleaningThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.refresh_after = 0
        self.lock = threading.Lock()
        
    def run(self):
        global threads
        while True:
            self.lock.acquire()
            new_threads = []
            for thread in threads:
                if thread.is_alive() or thread.online:
                    new_threads.append(thread)
            threads = new_threads
            self.lock.release()
            for i in range(10, 0, -1):
                self.refresh_after = i
                time.sleep(1)

class AddModelsThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.wanted = []
        self.lock = threading.Lock()
        self.repeatedModels = []
        self.counterModel = 0

    def run(self):
        global threads

        lines = open(settings['wishlist'], 'r').read().splitlines()
        self.wanted = (x for x in lines if x)
        self.lock.acquire()
        aux = []
        for model in self.wanted:
            model = model.lower()
            if model in aux:
                self.repeatedModels.append(model)
            else:
                aux.append(model)
                self.counterModel = self.counterModel + 1
                if not Model.isModelInListofObjects(model, threads) and not Model.isModelInListofObjects(model, recording_threads):
                    thread = Model(model, threads, recording_threads, post_processing)
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)
        for thread in recording_threads:
            if thread.model not in aux:
                thread.stop()
        self.lock.release()

if __name__ == '__main__':
    settings = config.readConfig()
    if 'postProcessingCommand' in settings:
        post_processing = PostProcessing(settings['postProcessingCommand'], settings['postProcessingThreads'] or 2)
    cleaningThread = CleaningThread()
    cleaningThread.daemon = True
    cleaningThread.start()

    while True:
        try:
            settings = config.readConfig()
            addModelsThread = AddModelsThread()
            addModelsThread.start()
            i = 1
            for i in range(settings['interval'], 0, -1):
                cls()
                if len(addModelsThread.repeatedModels):
                    print('The following models are more than once in wanted: [\'' + ', '.join(model for model in addModelsThread.repeatedModels) + '\']')
                print(f'{len(threads):02d} alive Threads (1 Thread per non-recording_threads model), cleaning dead/not-online Threads in {cleaningThread.refresh_after:02d} seconds, {addModelsThread.counterModel:02d} models in wanted')
                print(f'Online Threads (models): {len(recording_threads):02d}')
                print('The following models are being recorded:')
                for model_thread in recording_threads:
                    print(f'  Model: {model_thread.model}  -->  File: {os.path.basename(model_thread.file)}')
                print(f'Next check in {i:02d} seconds\r', end='')
                time.sleep(1)
            addModelsThread.join()
            del addModelsThread, i
        except:
            break
