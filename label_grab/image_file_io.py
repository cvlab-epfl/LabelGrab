from pathlib import Path
from PIL import Image
import numpy as np

def imread(path):
	return np.asarray(Image.open(path))

IMWRITE_OPTS = dict(
	webp = dict(quality = 90),
)

def imwrite(path, data, create_parent_dir=True):
	# TODO option to write in background thread

	path = Path(path)
	if create_parent_dir:
		path.parent.mkdir(exist_ok=True, parents=True)
	
	# log.info(f'write {path}')

	try:
		Image.fromarray(data).save(
			path, 
			**IMWRITE_OPTS.get(path.suffix.lower()[1:], {}),
		)
	except Exception as e:
		log.exception(f'Saving {path}')
