
from qtpy.QtCore import Qt, QObject, Signal, Slot, Property, QPointF, QRectF, QAbstractListModel
from qtpy.QtQuick import QQuickImageProvider
from qtpy.QtGui import QImage
import numpy as np
import cv2, imageio
import traceback
import qimage2ndarray
from operator import attrgetter





def bgr(r, g, b, a):
	return (b, g, r, a)


class GrabCutInstance:

	COLOR_OBJ_SURE = bgr(40, 250, 10, 175)
	COLOR_OBJ_GUESS = bgr(200, 200, 20, 128)
	COLOR_BGD_GUESS = bgr(120, 40, 20, 128)
	COLOR_BGD_SURE = bgr(250, 40, 10, 175)

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


	def draw_overlay(self, overlay):
		overlay_crop = overlay[self.crop_tl[1]:self.crop_br[1], self.crop_tl[0]:self.crop_br[0]]

		overlay_crop[:] = self.COLOR_TABLE[self.grab_cut_mask.reshape(-1)].reshape(overlay_crop.shape)

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


class ObjectInstance(QObject):
	def __init__(self, name, num):
		super().__init__()

		self.name = name
		self.num = num


	# nameChanged = Signal()
	# name = Property(str, attrgetter('name_'),notify=nameChanged)
	#
	# @name.setter
	# def setName(self, value):
	# 	self.name_ = value
	# 	self.nameChanged.emit()
	#
	# numChanged = Signal()
	# num = Property(int, attrgetter('num_'), notify=numChanged)
	#
	# @num.setter
	# def setName(self, value):
	# 	self.num_ = value
	# 	self.numChanged.emit()



class InstanceListModel(QAbstractListModel):

	item_fields = {
		Qt.UserRole + 1: 'name',
		Qt.UserRole + 2: 'num',
	}
	item_fields_inv = {name: role for role, name in item_fields.items()}
	item_fields_bytes = {role: bytes(name, 'ascii') for role, name in item_fields.items()}


	def __init__(self):
		super().__init__()

		self.instances = [
			ObjectInstance('tree', 1),
			ObjectInstance('tree', 2),
			ObjectInstance('car', 1),
		]

		#self.setRoleNames(dict(enumerate(['rolea'])))

		print('role names', self.roleNames())

	def __len__(self):
		return self.instances.__len__()

	def data(self, index, role):
		ret = getattr(self.instances[index.row()], self.item_fields[role])
		print(f'data[{index}] -> {index.row()} -> {ret}')
		return ret

	def roleNames(self):
		return self.item_fields_bytes

	def rowCount(self, index):
		#print('model::rowCount py ', self.__len__(), 'index=', index, index.row())
		return self.__len__()


	# @Slot(int)
	# def get(self, index):
	# 	print(f'model::get[{index}]')
	#
	# def headerData(self, section, orientation, role):
	# 	print(f'model::headerData({section}, {orientation}, {role})')

	# def __getattribute__(self, item):
	# 	print('model::attr ', item)
	# 	return super().__getattribute__(item)

from qtpy.QtGui import QStandardItemModel, QStandardItem

class LabelBackend(QObject):

	OverlayUpdated = Signal()


	def __init__(self):
		super().__init__()

		self.image_provider = LabelOverlayImageProvider()

		self.instance_list_model = InstanceListModel()

		# instances = [
		# 	ObjectInstance('tree', 1),
		# 	ObjectInstance('tree', 2),
		# 	ObjectInstance('car', 1),
		# ]
		# self.instance_list_model = QStandardItemModel(3, 1)
		#
		# for i, inst in enumerate(instances):
		# 	self.instance_list_model.setItem(0, i, inst)

	def set_image_path(self, img_path):
		self.photo = imageio.imread(img_path)
		self.resolution = np.array(self.photo.shape[:2][::-1])

		self.image_provider.init_image(self.resolution)
		self.overlay_data = self.image_provider.image_view

		self.OverlayUpdated.emit()


	# def get_instance_list_model(self):
	# 	return self.instance_list_model
	instanceListModelChanged = Signal()
	instanceListModel = Property(QObject, attrgetter('instance_list_model'), notify=instanceListModelChanged)

	@Slot(int, QPointF)
	def paint_circle(self, label_to_paint, center):
		try: # this has to finish, we don't want to break UI interaction
			print('paint_circle!', label_to_paint, center)

			center_pt = np.rint([center.x(), center.y()]).astype(dtype=np.int)

			self.instance.paint_circle(label_to_paint, center_pt)
			self.instance.grab_cut_update()
			self.instance.draw_overlay(self.overlay_data)

			self.OverlayUpdated.emit()

		except Exception as e:
			print('Error in paint_cirlce:', e)
			traceback.print_exc()


	@Slot(QRectF)
	def set_roi(self, roi_rect_qt):
		try: # this has to finish, we don't want to break UI interaction
			print('set roi!', roi_rect_qt)

			roi_rect = np.array([
				roi_rect_qt.topLeft().toTuple(),
				roi_rect_qt.bottomRight().toTuple(),
			])
			roi_rect = np.rint(roi_rect).astype(np.int)

			margin = 32

			crop_rect = np.array([
				np.maximum(roi_rect[0] - margin, 0),
				np.minimum(roi_rect[1] + margin, self.resolution),
			])

			self.instance = GrabCutInstance(self.photo, crop_rect, roi_rect)
			self.instance.grab_cut_init()
			self.instance.draw_overlay(self.overlay_data)

			self.OverlayUpdated.emit()

		except Exception as e:
			print('Error in paint_cirlce:', e)
			traceback.print_exc()

	@Slot(QObject)
	def use_instance_list(self, instance_list_obj):
		print('use instance list', instance_list_obj, dir(instance_list_obj))

		self.instance_list_qml = instance_list_obj


		#
		# print('rc', self.instance_list_qml.rowCount())
		# self.instance_list_qml.insert(1, ObjectInstance('tree', 1))
		# self.instance_list_qml.sync()
		# print('after insert')


		#insert_result = self.instance_list_qml.get(0)
		#, self.instance_list_qml.index(0, 0))
		#print('insert res', insert_result)

		#self.instance_list_model.dataChanged.emit()
		#self.instance_list_model.

		self.instance_list_model.dataChanged(self.instance_list_model.index(1, 0), InstanceListModel.item_fields_inv['name'])
