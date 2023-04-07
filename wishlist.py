import threading

import config
import log
from file_modified import FileModifiedHandler

settings = config.readConfig()

class Wishlist(threading.Thread):
    def __init__(self, wishlist_file):
        threading.Thread.__init__(self, daemon=True)
        self.wishlist = []
        self.wishlist_file = wishlist_file

    def reload(self):
        lines = []
        with open(self.wishlist_file, 'r') as f:
            lines = f.read().splitlines()

        new_list = []
        for model in lines:
            model = model.strip().lower()
            if not model or ' ' in model:
                continue
            if model in new_list:
                log.error(f'The {model} model is listed more than once in the wishlist')
                continue

            new_list.append(model)

        # Detect and print changes
        added = set(new_list).difference(self.wishlist)
        removed = set(self.wishlist).difference(new_list)
        if added:
            added_list = ', '.join(added)
            print(f'{added_list} models added')
        if removed:
            removed_list = ', '.join(removed)
            print(f'{removed_list} models removed')

        self.wishlist = new_list
        
    def run(self):
        self.reload()

        FileModifiedHandler(self.wishlist_file, self.reload)
        print('Not monitoring anymore')
