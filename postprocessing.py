import subprocess
import time
import queue
import threading
import os

processingQueue = queue.Queue()

class PostProcessing():
    def __init__(self, cmd, thread_count):
        if not cmd:
            return

        # TODO: Handle ffmpeg encoding within the app (with processing progress bar)
        self.cmd = cmd
        self.thread_count = thread_count
        self.queue = queue.Queue()
        self.workers = []
        self.sleep = 60

        self.start()

    def start(self):
        for i in range(0, self.thread_count):
            thread = threading.Thread(target=self.postProcess)
            thread.daemon = True
            thread.start()
            self.workers.append(thread)

    def add(self, item):
        self.queue.put(item)

    def postProcess(self):
        while True:
            while self.queue.empty():
                time.sleep(self.sleep)
                
            parameters = self.queue.get()
            path = parameters['path']
            filename = os.path.split(path)[-1]
            directory = os.path.dirname(path)
            file = os.path.splitext(filename)[0]
            subprocess.call(self.cmd.split() + [path, filename, directory, parameters['model'], file, 'cam4'])
