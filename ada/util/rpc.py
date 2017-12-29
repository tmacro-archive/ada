import zmq
import threading
import zlib
from .log import Log
import zmq.auth
import tempfile
import uuid

_log = Log('util.rpc')

class HandlerNotFound(Exception):
	pass

class InvalidArguements(Exception):
	pass

class RPCError(Exception):
	pass

class Message:
	def __init__(self):
		self._payload = {}

	@property
	def payload(self):
		return self._payload

	def setOption(self, key, value):
		self._payload[key] = value

	def getOption(self, key):
		return self._payload.get(key, None)

class Request(Message):
	def __init__(self, endpoint, args = {}):
		super().__init__()
		self.setOption('endpoint', endpoint)
		self.setOption('args', args)

	@property
	def endpoint(self):
		return self.getOption('endpoint')

	@property
	def args(self):
		return self.getOption('args')

class Response(Message):
	def __init__(self, success = True, results = None, error = False):
		super().__init__()
		self.setOption('success', success)
		self.setOption('results', results)
		self.setOption('error', error)

	@property
	def success(self):
		return self.getOption('success')

	@property
	def results(self):
		return self.getOption('results')

	@property
	def error(self):
		return self.getOption('error')

class BaseTransport(threading.Thread):
	def __init__(self, path):
		self._log = _log.getChild('transport %s'%path)
		self._path = path
		self._exit = threading.Event()
		self._watched = False
		self._type = None
		self._uuid = bytes(uuid.uuid4().hex.encode())
		super().__init__()
		
	def _open(self, path):
		self._log.debug('Opening zmq socket %s'%(self._path))
		self._context = zmq.Context() if not self._context else self._context
		self._socket = self._context.socket(self._type) if not self._socket else self._socket
		if self._type == zmq.REP:
			self._log.debug('Transport type is server, binding to socket')
			self._socket.bind(self._path)
		elif self._type == zmq.REQ:
			self._log.debug('Transport type is client, connecting to socket')
			self._socket.connect(self._path)

	def _recv(self, flags = 0):
		return self._socket.recv(flags = flags)
	
	def recv(self, noError = False, flags = 0):
		if self._watched and not noError:
			raise RPCError('You cannot recieve on a watched connection')
		try:
			self._log.debug('waiting for incoming data')
			data = self._recv(flags = flags)
		except zmq.ZMQError:
			return None
		# self._log.debug('recieved message %s'%data)
		return data

	def _send(self, message, **kwargs):
		# self._log.debug('Sending data %s'%message)
		self._socket.send(message, **kwargs)

	def send(self, *args, **kwargs):
		return self._send(*args, **kwargs)

	def _close(self):
		if self._watched:
			self._exit.set()
		self._socket.close()

	def _watch(self, handler):
		self._log.debug('setting up watcher')
		self._handler = handler
		self._watched = True
		self.start()

	def run(self):
		self._log.debug('watching for data')
		while not self._exit.isSet():
			ready = self._socket.poll(1000)
			if ready:
				self._log.debug('message recieved')
				message = self.recv(noError = True)
				self._handler(message)

class AuthTransport(BaseTransport):
	def __init__(self, path, server_pubkey = None):
		super().__init__(path)
		self._server_pubkey, _ = zmq.auth.load_certificate(server_pubkey)
		self._public, self._private = self._gen_key()
		
	def _open(self, path):
		self._context = zmq.Context()
		self._socket = self._context.socket(self._type)
		self._socket.curve_secretkey = self._private
		self._socket.curve_publickey = self._public
		self._socket.curve_serverkey = self._server_pubkey
		super()._open(path)
		
	def _gen_key(self):
		with tempfile.TemporaryDirectory() as key_dir:
			pub, priv = zmq.auth.create_certificates(key_dir, 'ephemeral')
			return zmq.auth.load_certificate(priv)

class JSONTransport(BaseTransport):
	def _recv(self, flags = 0):
		return self._socket.recv_json(flags = flags)

	def recv(self, *args, **kwargs):
		data = super().recv(*args, **kwargs)
		if not data:
			return None
		if self.type == zmq.REP:
			self._log.debug('returning Request')
			return Request(**data)
		if self.type == zmq.REQ:
			self._log.debug('returning response')
			return Response(**data)

	def _send(self, message):
		self._log.debug('sending data %s'%message.payload)
		self._socket.send_json(message.payload)


class GzipTransport(AuthTransport):
	def _send(self, message):
		self._log.debug('Compressing data')
		uncomp_size = str(len(message.payload['args']))
		comp = zlib.compress(message.payload['args'])
		super()._send(self._uuid, flags = zmq.SNDMORE)
		super()._send(bytes(uncomp_size.encode()), flags = zmq.SNDMORE)
		super()._send(comp)

	def _recv(self, *args, **kwargs):
		ruuid = super()._recv(*args, **kwargs)
		self._log.debug('stored: %s, received: %s'%(self._uuid, ruuid))
		assert ruuid == self._uuid
		data = super()._recv(*args, **kwargs)
		uncomp = zlib.decompress(data)
		self._log.debug('received message %s'%uncomp)
		return uncomp
	
	def recv(self, *args, **kwargs):
		data = super().recv(*args, **kwargs)
		if self._type == zmq.REQ:
			self._log.debug('returning Response')
			return Response(results = data)

class Server(JSONTransport):
	def __init__(self, path):
		super().__init__(path)
		self._log = _log.getChild('server: %s'%path)
		self._handlers = {}
		self.type = zmq.REP

	def open(self):
		super().open()
		self._watch(self._messageHandler)

	def addHandler(self, endpoint, func, mapping = {}): #mapping defines optional a required arguements eg {'foo': True, 'bar': False}
		self._handlers[endpoint] = dict(func = func, args = mapping)

	def _handle(self, endpoint, args):
		handler = self._handlers.get(endpoint, None)
		if not handler:
			raise HandlerNotFound('No handler found for %s'%endpoint)
		else:
			required = [x for x, y in handler['args'].items() if y] # These args are required
			optional = [x for x, y in handler['args'].items() if not y] # and these are optional
			for arg in args.keys():
				if arg in required:
					required.remove(arg)
				elif not arg in optional:
					raise InvalidArguements('extra arguement %s provided'%arg)
			if required:
				raise InvalidArguements('Not all required arguements provided %s'%required)
			return handler['func'](**args)

	def _call(self, request):
		try:
			result = self._handle(request.endpoint, request.args)
		except HandlerNotFound as e:
			return dict(success = False, error = 'HandlerNotFound')

		except InvalidArguements as e:
			return dict(success = False, error = str(e))

		return dict(success = True, results = result)

	def _messageHandler(self, message):
		response = Response(**self._call(message))
		self._send(response)



class Client(GzipTransport):
	def __init__(self, path, key):
		self._log = _log.getChild('client: %s'%path)
		super().__init__(path, key)
		self._type = zmq.REQ
		self._open(path)

	def _call(self, message):
		self.send(message)
		return self.recv()

	# def call(self, endoint, **kwargs):
	# 	req = Request(endoint, args = kwargs)
	# 	return self._call(req)

	def call(self, data):
		req = Request(None, args = data)
		return self._call(req)
		# return self.recv()
