
from qtpy.QtCore import Qt, QObject, Signal, Slot, Property, QPointF, QRectF
from qtpy.QtQuick import QQuickImageProvider
from qtpy.QtQml import QJSValue
from qtpy.QtGui import QImage

import numpy as np
import cv2, imageio
import traceback
import qimage2ndarray
from operator import attrgetter
from pathlib import Path


def bgr(r, g, b, a):
	return (b, g, r, a)


class GrabCutInstance:

	COLOR_OBJ_SURE = bgr(40, 250, 10, 100)
	COLOR_OBJ_GUESS = bgr(200, 200, 20, 50)
	COLOR_OBJ_CONTOUR = bgr(0, 255, 0, 200)

	COLOR_BGD_GUESS = bgr(120, 40, 20, 0)
	COLOR_BGD_SURE = bgr(250, 40, 10, 100)

	COLOR_TABLE = np.array([COLOR_BGD_SURE, COLOR_OBJ_SURE, COLOR_BGD_GUESS, COLOR_OBJ_GUESS])

	def __init__(self, photo, crop_rect, roi_rect):
		self.photo = photo

		self.crop_tl = crop_rect[0]
		self.crop_br = crop_rect[1]

		self.roi_tl = roi_rect[0] - self.crop_tl
		self.roi_br = roi_rect[1] - self.crop_tl

		self.photo_crop = self.photo[self.crop_tl[1]:self.crop_br[1], self.crop_tl[0]:self.crop_br[0]]


	def grab_cut_init(self):
		self.grab_cut_state = (
			np.zeros((1,65), np.float64),
			np.zeros((1,65), np.float64),
		)

		self.grab_cut_mask = np.zeros(self.photo_crop.shape[:2], dtype=np.uint8)
		cv2.grabCut(
			self.photo_crop,
			self.grab_cut_mask,
			tuple(np.concatenate([self.roi_tl, self.roi_br-self.roi_tl], axis=0)),
			self.grab_cut_state[0],
			self.grab_cut_state[1],
			5, cv2.GC_INIT_WITH_RECT,
		)


	def grab_cut_update(self):
		cv2.grabCut(
			self.photo_crop,
			self.grab_cut_mask,
			None,
			self.grab_cut_state[0],
			self.grab_cut_state[1],
			5, cv2.GC_INIT_WITH_MASK,
		)


	def paint_circle(self, label, center_pt):
		label_value = [cv2.GC_BGD, cv2.GC_FGD][label]

		center_pt = center_pt - self.crop_tl
		cv2.circle(self.grab_cut_mask, tuple(center_pt), 5, label_value, -1)


	def paint_polygon(self, label, points):
		label_value = [cv2.GC_BGD, cv2.GC_FGD][label]

		points_in_crop = points - self.crop_tl
		points_in_crop_int = np.rint(points_in_crop).astype(np.int32)

		cv2.drawContours(self.grab_cut_mask, [points_in_crop_int], 0, label, -1)

	def update_mask(self):
		self.mask = (self.grab_cut_mask == cv2.GC_FGD) | (self.grab_cut_mask == cv2.GC_PR_FGD)

		kernel = np.ones((5, 5), np.uint8)
		erosion = cv2.erode(self.mask.astype(np.uint8), kernel, iterations=1).astype(np.bool)

		self.contour_mask = self.mask & ~erosion
		self.contour_where = np.where(self.contour_mask)


	def draw_overlay(self, overlay):
		overlay_crop = overlay[self.crop_tl[1]:self.crop_br[1], self.crop_tl[0]:self.crop_br[0]]

		overlay_crop[:] = self.COLOR_TABLE[self.grab_cut_mask.reshape(-1)].reshape(overlay_crop.shape)

		self.update_mask()

		overlay_crop[self.contour_where] = self.COLOR_OBJ_CONTOUR


	def draw_mask(self, global_mask, label=1):
		mask_crop = global_mask[self.crop_tl[1]:self.crop_br[1], self.crop_tl[0]:self.crop_br[0]]
		mask_crop[self.mask] = label




		# def assign_reshape():
		# 	overlay_crop[:] = self.COLOR_TABLE[self.grab_cut_mask.reshape(-1)].reshape(overlay_crop.shape)
		#
		# def assign_equal():
		# 	overlay_crop[self.grab_cut_mask == cv2.GC_FGD] = self.COLOR_OBJ_SURE
		# 	overlay_crop[self.grab_cut_mask == cv2.GC_PR_FGD] = self.COLOR_OBJ_GUESS
		# 	overlay_crop[self.grab_cut_mask == cv2.GC_PR_BGD] = self.COLOR_BGD_GUESS
		# 	overlay_crop[self.grab_cut_mask == cv2.GC_BGD] = self.COLOR_BGD_SURE
		#
		# import timeit
		#
		# gl = dict(
		# 	assign_reshape = assign_reshape,
		# 	assign_equal=assign_equal,
		# )
		# n = int(1e4)
		# print('tm(reshape)  ', timeit.timeit('assign_reshape()', globals=gl, number=n))
		# print('tm(equal)    ', timeit.timeit('assign_equal()', globals=gl, number=n))
		# #tm(reshape) 10.847654940000211
		# #tm(equal) 18.054724517001887


class LabelOverlayImageProvider(QQuickImageProvider):
	QT_IMAGE_FORMAT = QImage.Format_ARGB32

	def __init__(self):
		# set the type use the requestImage method
		super().__init__(QQuickImageProvider.ImageType.Image)

	def init_image(self, resolution):
		self.resolution = resolution
		# apparently, using numpy values in QImage causes it to crash
		self.image_qt = QImage(int(resolution[0]), int(resolution[1]), self.QT_IMAGE_FORMAT)
		self.image_view = qimage2ndarray.byte_view(self.image_qt, 'little')
		# self.image_view = np.zeros((resolution[1], resolution[0], 4), np.uint8)
		print(f'byte view {self.image_view.shape} {self.image_view.dtype}')

		self.image_view[:] = 0

	def requestImage(self, id, size, requestedSize):
		print(f'requested img name={id} size={size} reqSize={requestedSize}')
		return self.image_qt


class InstanceGeometryInfo(QObject):
	def __init__(self, name, num, d):
		super().__init__()

		self.name_ = name
		self.num_ = num
		self.d = d


	xChanged = Signal()
	x = Property(float, notify=xChanged)
	
	@x.getter
	def getX(self):
		return float(self.d.crop_tl[0] + self.d.roi_tl[0])

	yChanged = Signal()
	y = Property(float, notify=yChanged)
	
	@y.getter
	def getX(self):
		return float(self.d.crop_tl[1] + self.d.roi_tl[1])

	widthChanged = Signal()
	width = Property(float, notify=widthChanged)
	@width.getter
	def getWidth(self):
		return float(self.d.roi_br[0] - self.d.roi_tl[0])

	heightChanged = Signal()
	height = Property(float, notify=heightChanged)
	@height.getter
	def getHeight(self):
		return float(self.d.roi_br[1] - self.d.roi_tl[1])


	nameChanged = Signal()
	name = Property(str, attrgetter('name_'),notify=nameChanged)
	
	@name.setter
	def setName(self, value):
		self.name_ = value
		self.nameChanged.emit()
	
	numChanged = Signal()
	num = Property(int, attrgetter('num_'), notify=numChanged)
	
	@num.setter
	def setName(self, value):
		self.num_ = value
		self.numChanged.emit()


class LabelBackend(QObject):

	OverlayUpdated = Signal()
	instanceAdded = Signal(QObject)

	@staticmethod
	def qml_point_to_np(qpoint : QPointF):
		return np.array(qpoint.toTuple())

	@staticmethod
	def qml_rect_to_np(qrect : QRectF):
		return np.array([
			qrect.topLeft().toTuple(),
			qrect.bottomRight().toTuple(),
		])

	def __init__(self):
		super().__init__()
		self.image_provider = LabelOverlayImageProvider()


	def set_image_path(self, img_path):
		print('Loading image', img_path)
		self.img_path = Path(img_path)
		self.photo = imageio.imread(self.img_path)
		self.resolution = np.array(self.photo.shape[:2][::-1])

		self.image_provider.init_image(self.resolution)
		self.overlay_data = self.image_provider.image_view

		self.instances = []

		self.OverlayUpdated.emit()


	@Slot(str)
	def setImage(self, path):
		path_prefix = "file://"
		if path.startswith(path_prefix):
			path = path[path_prefix.__len__():]

		self.set_image_path(path)


	@Slot(int, QPointF)
	def paint_circle(self, label_to_paint, center):
		try: # this has to finish, we don't want to break UI interaction
			print('paint_circle!', label_to_paint, center)

			center_pt = np.rint(center.toTuple()).astype(dtype=np.int)

			self.instance.paint_circle(label_to_paint, center_pt)
			self.instance.grab_cut_update()
			self.instance.draw_overlay(self.overlay_data)
			self.OverlayUpdated.emit()

		except Exception as e:
			print('Error in paint_circle:', e)
			traceback.print_exc()

	@Slot(int, QJSValue)
	def paint_polygon(self, label_to_paint, points):
		try:  # this has to finish, we don't want to break UI interaction

			points = np.array([p.toTuple() for p in points.toVariant()])
			print('paint_polygon!', label_to_paint, points)

			self.instance.paint_polygon(label_to_paint, points)
			self.instance.grab_cut_update()
			self.instance.draw_overlay(self.overlay_data)
			self.OverlayUpdated.emit()


		# center_pt = np.rint([center.x(), center.y()]).astype(dtype=np.int)
			#
			# self.instance.paint_circle(label_to_paint, center_pt)
			# self.instance.grab_cut_update()
			# self.instance.draw_overlay(self.overlay_data)
			#
			# self.OverlayUpdated.emit()

		except Exception as e:
			print('Error in paint_cirlce:', e)
			traceback.print_exc()

	@Slot(QRectF)
	def set_roi(self, roi_rect_qt):
		try: # this has to finish, we don't want to break UI interaction
			print('set roi!', roi_rect_qt)

			roi_rect = np.rint(self.qml_rect_to_np(roi_rect_qt)).astype(np.int)

			margin = 32

			crop_rect = np.array([
				np.maximum(roi_rect[0] - margin, 0),
				np.minimum(roi_rect[1] + margin, self.resolution),
			])

			self.instance = GrabCutInstance(self.photo, crop_rect, roi_rect)
			self.instance.grab_cut_init()
			self.instance.draw_overlay(self.overlay_data)

			self.instances.append(self.instance)

			self.OverlayUpdated.emit()


		except Exception as e:
			print('Error in set_roi:', e)
			traceback.print_exc()

	@Slot()
	def save(self):

		global_mask = np.zeros(tuple(self.resolution[::-1]), dtype=np.uint8)

		for inst_id, inst in enumerate(self.instances):
			inst.draw_mask(global_mask)

		path_base = self.img_path.parent / self.img_path.name

		imageio.imwrite(str(path_base) + '_labels.png', global_mask)
		imageio.imwrite(str(path_base) + '_labelsV.png', 255 * (global_mask > 0))
