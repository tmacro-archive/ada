from .app import app, websocket
# from flask import send_static_file
import numpy
from .audio.activity import vad_collector, frame_generator, convert_from_pcm, to_wave
from .audio.capture import AudioCapture
from .util.tools import xiter
from .util.log import Log
from .util.conf import config
import collections
import webrtcvad
import ada.util.rpc
from .util.rpc import Client
import time
_log = Log('ui')

vad = webrtcvad.Vad(3)

@app.route('/')
def index():
	return app.send_static_file('index.html')

@websocket.route('/audio')
def audio(ws):
	zmqClient = Client(config.zmq.path, config.zmq.pub_key)
	capture = AudioCapture(ws, buffer_ms = 1000)
	run = 0
	while True:
		captured = None
		for pcm, raw in xiter(capture(), 5): # Audio in 1 sec chunks
			frames = list(frame_generator(30, pcm, 16000))
			if list(vad_collector(16000, 30, 300, vad, frames)):
				captured = numpy.concatenate((captured, raw)) if not captured is None else raw
		ws.send('<--stop-->')
		time.sleep(0.5)
		_log.debug('Recording done')
		if not captured is None:
			wav = to_wave(captured, 16000)
			with open('test_clip%03i.wav'%run, 'wb'  ) as f:
				f.write(wav)
			resp = zmqClient.call(wav)
			_log.debug(resp.results)
			ws.send(resp.results)
			run += 1
		ws.send('<--start-->')		
		

		
		






		# print('Reported: %s'%rps)
		# 	# if vad.is_speech(frames[index:index+160], 16000):
		# frames = list(frame_generator(10, pcm, 16000))
		# for section in vad_collector(16000, 10, 50, vad, frames):
		# 		print('Detected')
		# samples = numpy.concatenate((samples, raw)) if not samples is None else raw

	# with open('test.wav', 'wb') as file:
	# 	file.write(wav)
	# print(wav)
