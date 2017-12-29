from .log import Log
import pyczmq

_log = Log('util.key')

def load_key(path):
	return pyczmq.zcert.load(path)

def save_key(path, key):
	return pyczmq.zert.save(cert, path)
