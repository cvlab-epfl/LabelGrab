

from qtpy.QtQuick import QQuickImageProvider
from qtpy.QtGui import QImage
import numpy as np
import cv2
import qimage2ndarray

class LabelOverlayImageProvider(QQuickImageProvider):
	QT_IMAGE_FORMAT = QImage.Format_ARGB32

	def __init__(self, *args, **kwargs):
		# set the type use the requestImage method
		super().__init__(QQuickImageProvider.ImageType.Image)

	def init_image(self, resolution):

		self.resolution = resolution
		self.image_qt = QImage(resolution[0], resolution[1], self.QT_IMAGE_FORMAT)
		self.image_view = qimage2ndarray.byte_view(self.image_qt, 'little')
		print(f'byte view {self.image_view.shape} {self.image_view.dtype}')

	def update(self):
		self.image_view[:] = 255
		self.image_view[:, :, 3] = 128
		self.image_view[:, :, 1] = 128
		self.image_view[:, :, 2] = 128

	def requestImage(self, id, size, requestedSize):
		print(f'requested img name={id} size={size} reqSize={requestedSize}')
		self.update()
		return self.image_qt
