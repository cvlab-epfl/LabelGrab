
def main():
	# qtpy: Unless overriden byt the QT_API env variable, use PySide2
	# This has to be setup before qtpy is imported
	import os
	os.environ.setdefault('QT_API', 'PySide2')

	from .application import run
	run()

if __name__ == '__main__':
	main()
