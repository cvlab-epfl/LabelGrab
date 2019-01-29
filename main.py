
#pip install numpy opencv-python imageio click qtpy pyside2 qimage2ndarray

#!/usr/bin/env python3
import os

if __name__ == '__main__':
	# qtpy: Unless overriden byt the QT_API env variable, use PySide2
	# This has to be setup before qtpy is imported
	os.environ.setdefault('QT_API', 'PySide2')

	from label_grab.application import main
	main()
