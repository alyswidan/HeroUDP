import time
def timeit(name):
    def inner(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            ret = func(*args, **kwargs)
            end = time.time()
            print(f'{name} took {end-start} s')
            return ret
        return wrapper
    return inner