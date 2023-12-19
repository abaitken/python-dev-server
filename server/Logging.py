LEVEL_TRACE = 1
LEVEL_MESSAGE = 2
LEVEL_INFO = 3
LEVEL_WARN = 4
LEVEL_ERROR = 5

Level = LEVEL_WARN

def Log(level, text):
    global Level
    if level >= Level:
        print(text)
