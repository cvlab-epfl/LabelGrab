
import logging, logging.handlers, sys
from pathlib import Path

def init_log():
	log = logging.getLogger(__name__)
	log.setLevel(logging.DEBUG)

	handler_stdout = logging.StreamHandler(sys.stdout)
	handler_stdout.setFormatter(
		logging.Formatter(fmt='{message}', style='{'),
	)
	handler_stdout.addFilter(lambda r: r.levelno <= logging.INFO)
	
	# write WARNING and above to stderr
	handler_stderr = logging.StreamHandler(sys.stderr)
	handler_stderr.setFormatter(
		logging.Formatter(fmt='{levelname:<7}|{filename}:{lineno}| {message}', style='{'),
	)
	handler_stderr.setLevel(logging.WARNING)

	for h in [handler_stdout, handler_stderr]: log.addHandler(h)

init_log()

