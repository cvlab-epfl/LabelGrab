

from qtpy.QtCore import QObject, Signal, Slot, QPointF
from qtpy.QtQuick import QQuickImageProvider
from qtpy.QtGui import QImage
import numpy as np
import cv2, imageio
import qimage2ndarray

class LabelOverlayImageProvider(QQuickImageProvider):
	QT_IMAGE_FORMAT = QImage.Format_ARGB32

	def __init__(self):
		# set the type use the requestImage method
		super().__init__(QQuickImageProvider.ImageType.Image)

	def init_image(self, resolution):
		self.resolution = resolution
		self.image_qt = QImage(resolution[0], resolution[1], self.QT_IMAGE_FORMAT)
		self.image_view = qimage2ndarray.byte_view(self.image_qt, 'little')
		print(f'byte view {self.image_view.shape} {self.image_view.dtype}')

		self.image_view[:] = 0

	def requestImage(self, id, size, requestedSize):
		print(f'requested img name={id} size={size} reqSize={requestedSize}')
		return self.image_qt

class LabelBackend(QObject):

	OverlayUpdated = Signal()

	def __init__(self):
		super().__init__()

		self.image_provider = LabelOverlayImageProvider()

	def set_image_path(self, img_path):
		self.photo = imageio.imread(img_path)

		self.image_provider.init_image(self.photo.shape[:2][::-1])
		self.overlay_data = self.image_provider.image_view

		self.OverlayUpdated.emit()

	@Slot(int, QPointF)
	def paint_circle(self, label_to_paint, center):
		print('paint_circle!', label_to_paint, center)

		center_pt = np.rint([center.x(), center.y()]).astype(dtype=np.int)

		cv2.circle(self.overlay_data, tuple(center_pt), 5, (255, 0, 0, 128), -1)

		self.OverlayUpdated.emit()
