import datetime
import threading
import os
import time
import streamlink
import requests

import config
import log

class Model(threading.Thread):
    def __init__(self, model, app):
        threading.Thread.__init__(self)
        self._stopevent = threading.Event()
        self.running = True

        settings = config.readConfig()

        self.model = model
        self.start_time = None
        self.app = app
        self.file = None
        self.directory = settings['save_directory']
        self.max_duration = settings['max_duration'] or 0
        self.online = None
        self.hls_source = None

    def generateFilename(self):
        settings = config.readConfig()
        now = datetime.datetime.now()
        self.file = settings['directory_structure'].format(
            path=self.directory,
            model=self.model, 
            seconds=now.strftime("%S"),
            minutes=now.strftime("%M"),
            hour=now.strftime("%H"),
            day=now.strftime("%d"),
            month=now.strftime("%m"),
            year=now.strftime("%Y")
        )

    def run(self):
        settings = config.readConfig()

        while self.running:
            isOnline = self.isOnline()
            if isOnline == False:
                if self.online:
                    self.stopRecording()
                time.sleep(settings['interval'])
                continue

            # Shouldn't happen? Another thread recording the same model?
            if self.app.isRecording(self.model):
                time.sleep(1)
                continue

            # Model is online - start recording
            self.startRecording()
            

    def info(self):
        ret = {
            'model': self.model,
            'online': self.online,
            'start_time': self.start_time,
        }

        ret['duration'] = datetime.datetime.now() - self.start_time
        ret['file_size'] = os.path.getsize(self.file)

        return ret

    def isOnline(self):
        try:
            model_url = f'https://chaturbate.com/api/chatvideocontext/{self.model}/'
            resp = requests.get(model_url)

            if resp.headers.get('content-type') != 'application/json':
                log.error(f'{self.model} couldn\'t be checked - filtered?')
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

    def startRecording(self):
        self.online = True
        self.generateFilename()
        print(f'{self.model} is online')
        self._stopevent.clear()
        self.start_time = datetime.datetime.now()

        try:
            session = streamlink.Streamlink()
            streams = session.streams(f'hlsvariant://{self.hls_source}')
            stream = streams['best']
            with stream.open() as hls_stream:
                os.makedirs(os.path.join(self.directory, self.model), exist_ok=True)
                
                f = open(self.file, 'wb')
                self.app.startRecording(self)

                while not (self._stopevent.isSet() or os.fstat(f.fileno()).st_nlink == 0):
                    try:
                        # Break file into 1h chunks
                        if self.max_duration:
                            delta = datetime.datetime.now() - self.start_time
                            minutes = delta.total_seconds() / 60
                            if minutes > self.max_duration:
                                self.app.processRecording(self.model, self.file, self.info()['duration'])
                                self.start_time = datetime.datetime.now()
                                self.generateFilename()
                                f = open(self.file, 'wb')

                        data = hls_stream.read(1024)
                        f.write(data)
                    except:
                        hls_stream.close()
                        break
            
        except Exception as e:
            log.exception(f'EXCEPTION: {e}')
        finally:
            if self.online:
                self.stopRecording()

    def stopRecording(self):
        self.online = False
        self.app.stopRecording(self)
        self.start_time = None
        self._stopevent.set()
        self.hls_source = None

        # If file is too small, delete it
        if self.file:
            try:
                if os.path.isfile(self.file) and os.path.getsize(self.file) <= 1024:
                    os.remove(self.file)
            except Exception as e:
                log.exception(f'EXCEPTION: {e}')

            self.file = None
