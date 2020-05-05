from multiprocessing import Process, Value
from time import sleep


def test(b: Value):
    sleep(1)
    b.value = True


if __name__ == '__main__':
    f = Value('b', False)
    p = Process(target=test, kwargs={'b': f})
    p.start()
    print(f.value)
    p.join()
    print(f.value)
