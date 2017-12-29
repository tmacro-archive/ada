from ..util.log import Log
from ..util.wsock import WSock
import collections
import numpy
from .activity import convert_to_pcm

_log = Log('util.capture')

class AudioCapture:
	def __init__(self, websocket, sample_rate = 16000, buffer_ms = 500):
		self._ws = WSock(websocket)
		self._recording = False
		self._ms = buffer_ms
		self._sample_rate = sample_rate
		self._samples = int(buffer_ms * sample_rate / 1000)
		self._buffer = None
		
	@property
	def id(self):
		return self._uuid
	
	def _grab_audio(self, data):
		return numpy.frombuffer(data, 'i2')

	def _process_audio(self, data):
		return convert_to_pcm(data, self._sample_rate), data

	def __call__(self):
		for msg in self._ws():
			if b'<--start-->' in msg:
				self._recording = True
				_log.debug('Starting Recording')
				continue
			if b'<--end-->' in msg:
				self._recording = False
				_log.debug('Stopping Recordng')
				continue
			if self._recording:
				audio = self._grab_audio(msg)
				self._buffer = numpy.concatenate((self._buffer, audio)) if not self._buffer is None else audio
				_log.debug('received: %s buffer: %s'%(len(self._buffer), self._samples))
				if len(self._buffer) >= self._samples:
					yield self._process_audio(numpy.array(self._buffer[:self._samples]))
					self._buffer = numpy.array(self._buffer[self._samples:])
