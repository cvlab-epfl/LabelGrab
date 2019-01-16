from pathlib import Path
import os, sys

from qtpy.QtGui import QGuiApplication
from qtpy.QtQml import QQmlApplicationEngine #, qmlRegisterType
#from qtpy.QtQuick import QQuickStyle
from qtpy.QtCore import QUrl

#from PySide2 import QtGui
# from PySide2.QtCore import QObject, QUrl
# from PySide2.QtGui import QGuiApplication
# from PySide2.QtQuick import QQuickView
# from PySide2.QtQml import qmlRegisterType, QQmlApplicationEngine
# from PySide2.QtCore import Signal, Slot, Property
#
# from PieChart import PieChart

from .label_backend import LabelOverlayImageProvider

def main():
	# Set default style to "fusion"
	# https://doc.qt.io/qt-5/qtquickcontrols2-styles.html#using-styles-in-qt-quick-controls-2
	os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'fusion')

	qt_app = QGuiApplication(sys.argv)

	# Init QML
	qml_engine = QQmlApplicationEngine()

	# tell it the location of qml files
	asset_dir = Path(__file__).parent / 'qml'
	qml_engine.addImportPath(str(asset_dir))

	# QML loads image from the backend using an image provider
	import imageio
	photo = imageio.imread(asset_dir / 'resources' / 'test.jpg')
	img_provider = LabelOverlayImageProvider()
	img_provider.init_image(photo.shape[:2][::-1])
	qml_engine.addImageProvider('label_overlay', img_provider)

	# Register backend classes
	#qmlRegisterType(PieChart, 'Charts', 1, 0, 'PieChart')

	# Load main window
	qml_engine.load(QUrl.fromLocalFile(str(asset_dir / 'main.qml')))

	if qml_engine.rootObjects():
		exit_code = qt_app.exec_()
		del qml_engine
		sys.exit(exit_code)
	else:
		print('QML failed to load')
		sys.exit(1)
