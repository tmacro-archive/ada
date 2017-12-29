from datetime import datetime, timedelta
import subprocess
from threading import *

class WatchedProcess(Thread):
	"""
		A light wrapper around a Popen object

		all args are passed through to the Popen constructor

		2 additional keyword arguments are added
			on_exit 
			on_error
		These should contain a callable object taking 1 arguement return_code
		on_exit will always be called when the process exits
		on_error will be called when the process exits with return_code != 0
	"""
		
	def __init__(self, *args, on_exit = None, on_error = None, **kwargs):
		super().__init__()
		self.daemon = True
		self._proc = None
		self._output = output
		self._started = Event()
		self._args = args
		self._kwargs = kwargs
		self._on_exit = on_exit
		self._on_error = on_error
	
	def __call__(self):
		"""for convenience return the popen object when called"""
		return self._proc

	def run(self):
		self._proc = subprocess.Popen(*self._args, **self._kwargs)
		self._started.set()
		self._proc.wait()
		rc = self._proc.returncode
		if self._on_exit:
			self._on_exit(rc)
		if self._on_error and rc != 0:
			self._on_error(rc)

	def terminate(self):
		return self._proc.terminate()
	
	def kill(self):
		return self._proc.kill()

	@property
	def status(self):
		if self._proc:
			return self._proc.poll()

	def wait(self):
		self._started.wait()
		# print(self._proc)
		return self._proc.wait() if self._proc else None
		

def WatchProcess(*args, start = True, **kwargs):
	wp = WatchedProcess(*args, **kwargs)
	if start:
		wp.start()
	return wp


def default_value(value):
	'''
		a simple decarator that returns a default value
		if the wrapped function returns None
	'''
	def outer(func):
		def inner(*args, **kwargs):
			ret = func(*args, **kwargs)
			return ret if not ret is None else value
		return inner
	return outer



def xiter(iter, x):
	for _ in range(x):
		yield next(iter)
