import logging
from .conf import config

levels = dict(
		critical = logging.CRITICAL,
		   error = logging.ERROR,
		 warning = logging.WARNING,
		    info = logging.INFO,
		   debug = logging.DEBUG
		   )

class Whitelist(logging.Filter):
    def __init__(self, *whitelist):
        self.whitelist = [logging.Filter(name) for name in whitelist]

    def filter(self, record):
        return any(f.filter(record) for f in self.whitelist)

class Blacklist(Whitelist):
    def filter(self, record):
        return not Whitelist.filter(self, record)

def formatter():
	return logging.Formatter(fmt=config.logging.logfmt, datefmt=config.logging.datefmt)


def setupLogging():
	# Create our root logger and set the log lvl
	rootLogger = logging.getLogger()
	rootLogger.setLevel(config.logging.loglvl)

	# Setup formatting
	# formatter = logging.Formatter(fmt=config.logging.logfmt, datefmt=config.logging.datefmt)

	# Add logging to stdout
	streamHandler = logging.StreamHandler()
	streamHandler.setFormatter(formatter())

	rootLogger.addHandler(streamHandler)

	# Setup log files and rotation if enabled
	if config.logging.logfile:
		if config.logging.log_rotation:
			handler = logging.handlers.RotatingFileHandler(
				config.logging.logfile, maxBytes=10*1024*1024, backupCount=2)
		else:
			handler = logging.FileHandler(config.logging.logfile)

		handler.setFormatter(formatter())
		rootLogger.addHandler(handler)

	for handler in logging.root.handlers:
		handler.addFilter(Blacklist('urllib3.connectionpool', 'capturebate.api.method', 'capturebate.api.client.CBClient'))
	baseLogger = logging.getLogger(config.meta.app)
	baseLogger.info('Starting %s: version %s'%(config.meta.app, config.meta.version))
	return baseLogger

BASE_LOGGER = setupLogging()

# return a nested child of root 
# levels are indicated in name by "."
# eg. "root.foo.bar"
def get_logger(root, name):
	if not '.' in name:
		return root.getChild(name)
	lvl = name.split('.')
	return get_logger(root.getChild(lvl.pop(0)), '.'.join(lvl))

def Log(name):
	baselogger = BASE_LOGGER if BASE_LOGGER else logging.getLogger('root')
	return get_logger(baselogger, name)

def log_on_error(logger, target_handler = None, flush_lvl = logging.ERROR, capacity = 250):
	if target_handler is None:
		target_handler = logging.StreamHandler()
		target_handler.setFormatter(formatter())
	handler = logging.handlers.MemoryHandler(capacity, flushLevel = flush_lvl, target = target_handler)

	def decorator(fn):
		def wrapper(*args, **kwargs):
			logger.addHandler(handler)
			try:
				return fn(*args, **kwargs)
			except Exception:
				raise
			finally:
				super(logging.handlers.MemoryHandler, handler).flush()
				logger.removeHandler(handler)
		return wrapper
	return decorator
