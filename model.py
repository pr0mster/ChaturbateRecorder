import datetime
import threading
import os
import streamlink
import requests

import config
import log

class Model(threading.Thread):
    def __init__(self, model, threads, recording_threads, post_processing):
        threading.Thread.__init__(self)
        self.model = model
        self._stopevent = threading.Event()
        self.file = None
        self.online = None
        self.hls_source = None
        self.lock = threading.Lock()
        self.threads = threads
        self.recording_threads = recording_threads
        self.post_processing = post_processing

    def run(self):
        settings = config.readConfig()

        isOnline = self.isOnline()
        if isOnline == False:
            self.online = False
            self.hls_source = None

            return

        self.online = True
        now = datetime.datetime.now()
        self.file = settings['directory_structure'].format(
            path=settings['save_directory'],
            model=self.model, 
            seconds=now.strftime("%S"),
            minutes=now.strftime("%M"),
            hour=now.strftime("%H"),
            day=now.strftime("%d"),
            month=now.strftime("%m"),
            year=now.strftime("%Y")
        )
        try:
            session = streamlink.Streamlink()
            streams = session.streams(f'hlsvariant://{self.hls_source}')
            stream = streams['best']
            fd = stream.open()
            if not self.isModelInListofObjects(self.model, self.recording_threads):
                os.makedirs(os.path.join(settings['save_directory'], self.model), exist_ok=True)
                with open(self.file, 'wb') as f:
                    self.lock.acquire()
                    self.recording_threads.append(self)
                    for index, thread in enumerate(self.threads):
                        if thread.model == self.model:
                            del self.threads[index]
                            break
                    self.lock.release()
                    while not (self._stopevent.isSet() or os.fstat(f.fileno()).st_nlink == 0):
                        try:
                            data = fd.read(1024)
                            f.write(data)
                        except:
                            fd.close()
                            break
                if self.post_processing:
                    self.post_processing.add({'model': self.model, 'path': self.file})
        except Exception as e:
            log(f'EXCEPTION: {e}')
            self.stop()
        finally:
            self.exceptionHandler()

    @staticmethod
    def isModelInListofObjects(obj, lista):
        result = False
        for i in lista:
            if i.model == obj:
                result = True
                break
        return result

    def exceptionHandler(self):
        self.stop()

    def isOnline(self):
        try:
            model_url = f'https://chaturbate.com/api/chatvideocontext/{self.model}/'
            resp = requests.get(model_url)

            if resp.headers.get('content-type') != 'application/json':
                print(f'CloudFlare filtering {self.model}')
                return False

            hls_url = ''
            if 'hls_source' in resp.json():
                hls_url = resp.json()['hls_source']
            if len(hls_url):
                self.hls_source = hls_url
                return True
            else:
                self.hls_source = True
                return False
        except Exception as e:
            print(e)
            return False

    def stop(self):
        self._stopevent.set()
        self.online = False
        self.lock.acquire()
        for index, thread in enumerate(self.recording_threads):
            if thread.model == self.model:
                del self.recording_threads[index]
                break
        self.lock.release()
        try:
            file = os.path.join(os.getcwd(), self.file)
            if os.path.isfile(file):
                if os.path.getsize(file) <= 1024:
                    os.remove(file)
        except Exception as e:
            log(f'EXCEPTION: {e}')
