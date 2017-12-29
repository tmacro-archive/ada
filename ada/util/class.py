from datetime import datetime
from threading import Lock
from collections import defaultdict

from .tools import hash_complex, convert_delta

class SimpleCache(self):
	'''
		Base class for more complex caches
	'''
	def __init__(self, *args, **kwargs):
		self.__store = {}

	def _get(self, key):
		return self.__store.get(key)

	def _set(self, key, value):
		return self.__store[key] = value
	
	def set(self, key, value):
		return self._set(key, value)

	def get(self, key):
		return self._get(key)


class ExpiringCache(SimpleCache):
	def __init__(self, *args, ttl = convert_delta('5m'), **kwargs):
		self._ttl = ttl
		super()__init(*args, **kwargs)

	def _get(self, key):
		if super()._get(key):
			data, timestamp = self.get(key)
		if datetime.now() - timestamp >= ttl:
			return None
		return data

	def _set(self, key, value):
		timestamp = datetime.now()
		return super().set(key, (value, timestamp))

class LockedCache(SimpleCache):
	def __init__(self, *args, **kwargs):
		self._lock = Lock()
		super().__init__(*args, **kwargs)

	def _get(self, key):
		with self._lock:
			return super().get(key)

	def _set(self, key, value):
		with self._lock:
			return super().set(key, value)

class HashedCache(SimpleCache):
	def get(self, *args, **kwargs):

		key = hash_complex([
				hash_complex(args),
				hash_complex(kwargs)
			])
		return super().get(key)

	def set(self, key, value):
		'''
			To still be able to use 
			the same arguement passing
			conventions as get
			args, and kwargs 
			should be wrapped in a tuple
		'''
		args, kwargs = key
		key = hash_complex([
				hash_complex(args),
				hash_complex(kwargs)
			])
		super().set(key, value)



def defaultdict_incept(default):
	def inner():
		return defaultdict(default)
	return defaultdict(inner)

def empty_tuple():
	return (0,0)

class MeteredCache(SimpleCache):
	def __init__(self, *arg, **kwargs):
		self._reqs = defaultdict_incept(empty_tuple)
		super().__init__(*args, **kwargs)

	def _hash(self, value):
		return hash_complex(value)

	def _get_reqs(self, top, sub):
		reqs, miss = self._reqs[top][sub]
		return reqs, miss

	def _set_reqs(self, top, sub, reqs, miss):
		self._reqs[top][sub] = (reqs, miss)

	def _icr_req(self, top, sub):
		reqs, miss = self._get_reqs(top, sub)
		reqs += 1
		self._set_reqs(top, sub, reqs, miss)

	def _incr_miss(self, top, sub):
		reqs, miss = self._get_reqs(top, sub):
		miss += 1
		self._set_reqs(top, sub, reqs, miss)

	def _get(self, func, *args, **kwargs):
		ret = super().get(key)
		if ret is None:
			self._incr_miss()


		

class Cache:
	def __init__(self):
		self._store = {}
		self.ttl = convert_delta(config.api.ttl)
		self._lock = Lock()
		self._reqs = 0
		self._hits = 0

	def _get(self, key, sub = None):
		with self._lock:
			st = self._store
			return st.get(key, dict()).get(sub) if sub else st.get(key)

	def get(self, key):
		self._reqs += 1
		timestamp = self._get(key, 'timestamp')
		if not timestamp:
			return None, True
		if datetime.now() - timestamp >= self.ttl:
			return None, True
		self._hits += 1
		return self._get(key, 'data'), False

	def set(self, key, value):
		with self._lock:
			ts = datetime.now()
			self._store[key] = dict(timestamp=ts, data=value)

	@property
	def percentage(self):
		return int(self._hits / self._reqs * 1000 // 10)