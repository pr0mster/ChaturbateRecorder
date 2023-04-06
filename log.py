import datetime

def log(message):
    with open('log.log', 'a+') as f:
        f.write(f'\n{datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")} {message}\n')