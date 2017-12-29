from .log import get_logger


class WSock:
	def __init__(self, websocket):
		self._ws = websocket

	def __call__(self):
		while True:
			msg = self._ws.receive()
			if not msg:
				continue
			yield msg
