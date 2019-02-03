from pathlib import Path
import os, sys
import click
from qtpy.QtCore import QUrl
from qtpy.QtGui import QGuiApplication
from qtpy.QtQml import QQmlApplicationEngine

from .label_backend import LabelBackend

DIR_SOURCE =  Path(__file__).parent
DIR_RESOURCES = DIR_SOURCE / 'resources'

@click.command()
@click.option('--config', type=click.Path(exists=True, dir_okay=False), default=DIR_RESOURCES / 'config' / 'default_classes.json')
# @click.option('--dir_in', type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
# @click.option('--dir_out', type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=None)
def main(config):
	# Set default style to "fusion"
	# https://doc.qt.io/qt-5/qtquickcontrols2-styles.html#using-styles-in-qt-quick-controls-2
	#os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'fusion')

	qt_app = QGuiApplication(sys.argv)
	qt_app.setOrganizationName("EPFL")
	qt_app.setOrganizationDomain("ch")

	# Init QML
	qml_engine = QQmlApplicationEngine()

	# tell it the location of qml files
	qml_engine.addImportPath(str(DIR_RESOURCES))

	# Register backend classes
	backend = LabelBackend()
	backend.load_config(Path(config))
	backend.set_image_path(DIR_RESOURCES / 'images' / 'test.jpg')
	qml_engine.rootContext().setContextProperty('backend', backend)

	# QML loads image from the backend using an image provider
	qml_engine.addImageProvider('backend', backend.image_provider)

	# Load main window
	qml_engine.load(QUrl.fromLocalFile(str(DIR_RESOURCES / 'main.qml')))

	if qml_engine.rootObjects():
		exit_code = qt_app.exec_()
		del qml_engine
		sys.exit(exit_code)
	else:
		print('QML failed to load')
		sys.exit(1)
