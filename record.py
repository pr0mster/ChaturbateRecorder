import time
import os
import threading

from model import Model
from wishlist import Wishlist
from monitor import Monitor
import config
import log

# Enable ANSI escape sequence processing in Windows
if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

screen_refresh = 1

settings = {}
threads = []

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == '__main__':
    settings = config.readConfig()
    try:
        wishlist = Wishlist(settings['wishlist'])
        wishlist.start()

        app = Monitor(wishlist)
        app.start()
        
        # TODO: Key to force-refresh models?
        
        while True:
            for i in range(settings['interval'], 0, -screen_refresh):
                time.sleep(screen_refresh)
                cls()
                if len(app.done) > 0:
                    print('Completed:')
                    for done in app.done:
                        print(f'[{done["duration"]}] {done["path"]}')
                
                print(f'{len(app.monitoring_threads)} offline + {len(app.recording_threads)} online models, {len(wishlist.wishlist)} models in wishlist')
                if len(app.recording_threads) > 0:
                    print('The following models are being recorded:')
                    for model_thread in app.recording_threads.values():
                        file_info = model_thread.info()
                        duration = file_info['duration']
                        file_size = file_info['file_size'] / 1024 / 1024
                        print(f'  Model: {model_thread.model:30s}  -->  [{duration}] {model_thread.file} ({file_size:0.2f}Mb)')
                print(f'Next check in {i:02d} seconds\r', end='')

    except KeyboardInterrupt:
        pass
    except Exception as e:
        log.exception(e)

    print('Shutting down')
    if len(app.done) > 0:
        print(f'Completed {len(app.done)} recordings:')
        for done in app.done:
            print(f'[{done["duration"]}] {done["path"]}')
