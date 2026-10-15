MIN_TIMEOUT = 1
MAX_TIMEOUT = 300


def parse_timeout(value):
    if type(value) is not int:
        raise TypeError("timeout must be an int")
    if value < MIN_TIMEOUT or value > MAX_TIMEOUT:
        raise ValueError("timeout must be between 1 and 300")
    return value
