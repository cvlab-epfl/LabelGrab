
from qtpy.QtCore import Qt, QObject, Signal, Slot, Property, QPointF, QRectF
from qtpy.QtQuick import QQuickImageProvider
from qtpy.QtQml import QJSValue
from qtpy.QtGui import QImage, QColor

import numpy as np
import cv2, imageio
import traceback
import qimage2ndarray
from collections import namedtuple
from operator import attrgetter
from pathlib import Path
import json, zipfile


def bgr(r, g, b, a):
	return (b, g, r, a)


class GrabCutInstance:

	COLOR_OBJ_SURE = bgr(40, 250, 10, 100)
	COLOR_OBJ_GUESS = bgr(200, 200, 20, 50)
	COLOR_OBJ_CONTOUR = bgr(0, 255, 0, 200)

	COLOR_BGD_GUESS = bgr(120, 40, 20, 0)
	COLOR_BGD_SURE = bgr(250, 40, 10, 100)

	COLOR_TABLE = np.array([COLOR_BGD_SURE, COLOR_OBJ_SURE, COLOR_BGD_GUESS, COLOR_OBJ_GUESS])

	ALPHA_CONTOUR = 255
	ALPHA_CLASS_COLOR = 150

	MORPH_KERNEL = np.ones((3, 3), np.uint8)



	def __init__(self, instance_id, semantic_class, photo, crop_rect, roi_rect):
		self.id = instance_id
		self.semantic_class = semantic_class
		self.photo = photo

		self.crop_rect = crop_rect
		self.roi_rect = roi_rect

		self.crop_tl = crop_rect[0]
		self.crop_br = crop_rect[1]

		self.roi_tl = roi_rect[0] - self.crop_tl
		self.roi_br = roi_rect[1] - self.crop_tl

		self.photo_crop = self.photo[self.crop_tl[1]:self.crop_br[1], self.crop_tl[0]:self.crop_br[0]]


	def grab_cut_init(self):
		self.grab_cut_state = np.zeros((2,65), np.float64)

		self.grab_cut_mask = np.zeros(self.photo_crop.shape[:2], dtype=np.uint8)
		cv2.grabCut(
			self.photo_crop,
			self.grab_cut_mask,
			tuple(np.concatenate([self.roi_tl, self.roi_br-self.roi_tl], axis=0)),
			self.grab_cut_state[0:1],
			self.grab_cut_state[1:2],
			5, cv2.GC_INIT_WITH_RECT,
		)

		self.update_mask()


	def grab_cut_update(self):
		cv2.grabCut(
			self.photo_crop,
			self.grab_cut_mask,
			None,
			self.grab_cut_state[0:1],
			self.grab_cut_state[1:2],
			5, cv2.GC_INIT_WITH_MASK,
		)

		self.update_mask()


	def paint_circle(self, label, center_pt):
		label_value = [cv2.GC_BGD, cv2.GC_FGD][label]

		center_pt = center_pt - self.crop_tl
		cv2.circle(self.grab_cut_mask, tuple(center_pt), 5, label_value, -1)

		self.update_mask()


	def paint_polygon(self, label, points):
		label_value = [cv2.GC_BGD, cv2.GC_FGD][label]

		points_in_crop = points - self.crop_tl
		points_in_crop_int = np.rint(points_in_crop).astype(np.int32)

		cv2.drawContours(self.grab_cut_mask, [points_in_crop_int], 0, label_value, -1)

		self.update_mask()


	def update_mask(self):
		self.mask = (self.grab_cut_mask == cv2.GC_FGD) | (self.grab_cut_mask == cv2.GC_PR_FGD)


		erosion = cv2.erode(self.mask.astype(np.uint8), self.MORPH_KERNEL, iterations=1).astype(np.bool)

		self.contour_mask = self.mask & ~erosion
		self.contour_where = np.where(self.contour_mask)


	def draw_overlay_edit_interface(self, overlay):
		overlay_crop = overlay[self.crop_tl[1]:self.crop_br[1], self.crop_tl[0]:self.crop_br[0]]
		overlay_crop[:] = self.COLOR_TABLE[self.grab_cut_mask.reshape(-1)].reshape(overlay_crop.shape)
		overlay_crop[self.contour_where] = self.COLOR_OBJ_CONTOUR

	def draw_overlay_contour(self, overlay):
		overlay_crop = overlay[self.crop_tl[1]:self.crop_br[1], self.crop_tl[0]:self.crop_br[0]]

		class_color = self.semantic_class.color

		overlay_crop[self.mask] = np.concatenate([class_color, [self.ALPHA_CONTOUR]], axis=0)
		overlay_crop[self.contour_where] = np.concatenate([class_color, [self.ALPHA_CLASS_COLOR]], axis=0)

	def draw_mask(self, global_mask, label=None):

		if label is None:
			label = self.semantic_class.id

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

	def to_dict(self):
		return dict(
			id=self.id, cls=self.semantic_class.id,
			crop_rect=self.crop_rect.tolist(), roi_rect = self.roi_rect.tolist(),
		)

	def save_to_dir(self, dir_path):
		imageio.imwrite(dir_path / f'instance_{self.id:03d}_gc_mask.png', self.grab_cut_mask)
		np.save(dir_path / f'instance_{self.id:03d}_gc_state.npy', self.grab_cut_state)

	def load_from_dir(self, dir_path):
		self.grab_cut_mask = imageio.imread(dir_path / f'instance_{self.id:03d}_gc_mask.png')
		self.grab_cut_state = np.load(dir_path / f'instance_{self.id:03d}_gc_state.npy')
		self.update_mask()

	@staticmethod
	def from_dict(saved_info, config, photo):

		inst = GrabCutInstance(
			saved_info['id'], config.classes_by_id[saved_info['cls']], photo,
			np.array(saved_info['crop_rect']), np.array(saved_info['roi_rect']),
		)
		return inst


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


class LabelConfig:

	SemanticClass = namedtuple('LabelClass', ['id', 'name', 'color'])

	def __init__(self):
		self.set_classes([
			self.SemanticClass(2, 'anomaly', self.convert_color('orangered'))
		])

	def set_classes(self, classes):
		self.classes = classes
		self.classes_by_id = {cls.id: cls for cls in classes}

	@staticmethod
	def convert_color(color_json):

		# named color
		if isinstance(color_json, str):

			qc = QColor(color_json.lower())

			if qc.isValid():
				return np.array(qc.toTuple(), dtype=np.uint8)[:3]
			else:
				# http://doc.qt.io/qt-5/qml-color.html
				raise ValueError(f'Invalid color name {color_json}, please use SVG names')

		else:
			color = np.array(color_json)

			if color.__len__() != 3:
				raise ValueError(f'Color should be [r, g, b] but received wrong length: {color_json}')

			if issubclass(color.dtype, np.floating):
				color *= 255

			return color.astype(np.uint8)


	def load_from_path(self, path):
		with Path(path).open('r') as f_in:
			content_json = json.load(f_in)

		self.set_classes([
			self.SemanticClass(cls_json['id'], cls_json['name'], self.convert_color(cls_json['color']))
			for cls_json in content_json['classes']
		])


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

		self.config = LabelConfig()

	def load_config(self, cfg_path):
		if cfg_path.is_file():
			self.config.load_from_path(cfg_path)
		else:
			print(f'Config path {cfg_path} is not a file')

	def set_image_path(self, img_path):
		print('Loading image', img_path)

		self.img_path = Path(img_path)
		self.photo = imageio.imread(self.img_path)
		self.resolution = np.array(self.photo.shape[:2][::-1])

		self.image_provider.init_image(self.resolution)
		self.overlay_data = self.image_provider.image_view

		self.instances = []

		data_dir = self.img_path.with_suffix('.labels')
		if data_dir.is_dir():
			print(f'Loading saved state from {data_dir}')

			self.load(data_dir)

		self.next_instance_id = int(np.max([0] + [inst.id for inst in self.instances]) + 1)
		self.instances_by_id = {inst.id: inst for inst in self.instances}
		self.instance_selected = None

		self.overlay_refresh_after_selection_change()


	@Slot(str)
	def setImage(self, path):
		path_prefix = "file://"
		if path.startswith(path_prefix):
			path = path[path_prefix.__len__():]

		self.set_image_path(path)


	@Slot(int, QPointF)
	def paint_circle(self, label_to_paint, center):
		try: # this has to finish, we don't want to break UI interaction
			#print('paint_circle!', label_to_paint, center)

			if self.instance_selected:
				center_pt = np.rint(center.toTuple()).astype(dtype=np.int)

				self.instance_selected.paint_circle(label_to_paint, center_pt)
				self.instance_selected.grab_cut_update()
				self.overlay_refresh_after_edit()
			else:
				print('paint_circle: no instance is selected')

		except Exception as e:
			print('Error in paint_circle:', e)
			traceback.print_exc()

	@Slot(int, QJSValue)
	def paint_polygon(self, label_to_paint, points):
		try:  # this has to finish, we don't want to break UI interaction

			if self.instance_selected:
				points = np.array([p.toTuple() for p in points.toVariant()])
				#print('paint_polygon!', label_to_paint, points)

				self.instance_selected.paint_polygon(label_to_paint, points)
				self.instance_selected.grab_cut_update()
				self.overlay_refresh_after_edit()
			else:
				print('paint_polygon: no instance is selected')

		except Exception as e:
			print('Error in paint_polygon:', e)
			traceback.print_exc()

	def overlay_refresh_after_selection_change(self):
		if self.instance_selected:

			self.overlay_data[:] = (0, 0, 0, 128)
			self.instance_selected.draw_overlay_edit_interface(self.overlay_data)

		else:

			self.overlay_data[:] = 0

			for inst in self.instances:
				inst.draw_overlay_contour(self.overlay_data)

		self.OverlayUpdated.emit()


	def overlay_refresh_after_edit(self):
		if self.instance_selected:
			self.instance_selected.draw_overlay_edit_interface(self.overlay_data)
			self.OverlayUpdated.emit()
		else:
			print('overlay_refresh_after_edit but instance_selected is null')


	@Slot(int)
	def select_instance(self, instance_id):
		if instance_id <= 0:
			instance_id = None

		if instance_id:
			self.instance_selected = self.instances_by_id[instance_id]
		else:
			self.instance_selected = None

		self.overlay_refresh_after_selection_change()

	@Slot(QRectF)
	def new_instance(self, roi_rect_qt):
		try: # this has to finish, we don't want to break UI interaction
			roi_rect = np.rint(self.qml_rect_to_np(roi_rect_qt)).astype(np.int)
			print('new instance!', roi_rect)

			margin = 32
			crop_rect = np.array([
				np.maximum(roi_rect[0] - margin, 0),
				np.minimum(roi_rect[1] + margin, self.resolution),
			])

			instance = GrabCutInstance(self.next_instance_id, self.config.classes[0], self.photo, crop_rect, roi_rect)
			self.next_instance_id += 1
			self.instances.append(instance)
			self.instances_by_id[instance.id] = instance

			instance.grab_cut_init()

			self.select_instance(instance.id)

		except Exception as e:
			print('Error in new_instance:', e)
			traceback.print_exc()

	@Slot(int)
	def delete_instance(self, instance_id):
		inst = self.instances_by_id[instance_id]

		if self.instance_selected == inst:
			self.select_instance(-1)

		del self.instances_by_id[instance_id]
		self.instances.remove(inst)
		self.overlay_refresh_after_selection_change()


	@Slot()
	def save(self):

		# outputs
		sem_map = np.zeros(tuple(self.resolution[::-1]), dtype=np.uint8)
		sem_colorimg = np.zeros(tuple(self.resolution[::-1]) + (3,), dtype=np.uint8)
		inst_map = np.zeros(tuple(self.resolution[::-1]), dtype=np.uint8)

		for inst_id, inst in enumerate(self.instances):
			inst.draw_mask(sem_map)
			inst.draw_mask(sem_colorimg, inst.semantic_class.color)
			inst.draw_mask(inst_map, inst_id+1)

		out_dir = self.img_path.with_suffix('.labels')
		out_dir.mkdir(exist_ok=True)

		imageio.imwrite(out_dir / 'labels_semantic.png', sem_map)
		imageio.imwrite(out_dir / 'labels_semantic_color.png', sem_colorimg)
		imageio.imwrite(out_dir / 'labels_instance.png', inst_map)

		# internal state

		json_data = dict(
			instances = [inst.to_dict() for inst in self.instances]
		)

		with (out_dir / 'index.json').open('w') as f_out:
			json.dump(json_data, f_out, indent='	')

		for inst in self.instances:
			inst.save_to_dir(out_dir)

	def load(self, in_dir):
		with (in_dir / 'index.json').open('r') as f_in:
			json_data = json.load(f_in)

		self.instances = [
			GrabCutInstance.from_dict(inst_data, self.config, self.photo)
			for inst_data in json_data['instances']
		]

		for inst in self.instances:
			inst.load_from_dir(in_dir)

