
from qtpy.QtCore import Qt, QObject, QUrl, Signal, Slot, Property, QPointF, QRectF
from qtpy.QtQuick import QQuickImageProvider
from qtpy.QtQml import QJSValue
from qtpy.QtGui import QImage, QColor, QKeySequence

import numpy as np
import cv2, imageio
import traceback
import qimage2ndarray
from collections import namedtuple
from operator import attrgetter
from pathlib import Path
import json, zipfile

import logging
log = logging.getLogger(__name__)

def bgr(r, g, b, a):
	return (b, g, r, a)


class GrabCutInstance(QObject):

	GRAB_CUT_NUM_ITER = 5

	COLOR_OBJ_SURE = bgr(40, 250, 10, 100)
	COLOR_OBJ_GUESS = bgr(200, 200, 20, 50)
	COLOR_OBJ_CONTOUR = bgr(0, 255, 0, 200)

	COLOR_BGD_GUESS = bgr(120, 40, 20, 0)
	COLOR_BGD_SURE = bgr(250, 40, 10, 100)

	COLOR_TABLE = np.array([COLOR_BGD_SURE, COLOR_OBJ_SURE, COLOR_BGD_GUESS, COLOR_OBJ_GUESS])

	ALPHA_CONTOUR = 255
	ALPHA_CLASS_COLOR = 150

	MORPH_KERNEL = np.ones((3, 3), np.uint8)


	def __init__(self, backend, instance_id, semantic_class, photo, crop_rect, roi_rect):
		super().__init__()

		self.backend = backend
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

		self.depth_index = self.backend.depth_index_new()

		self.update_qt_info()

	def grab_cut_init(self, existing_instance_mask_global=None):

		self.grab_cut_state = np.zeros((2,65), np.float64)
		self.grab_cut_mask = np.full(self.photo_crop.shape[:2], cv2.GC_PR_BGD, dtype=np.uint8)

		# sometimes grab cut throws an exception because it finds no foreground in the whole roi
		# we help it then by marking the central pixel as foreground
		def set_center_pixel_to_foreground():
			sh_c = np.array(self.grab_cut_mask.shape) // 2
			sh_l = sh_c - 2
			sh_r = sh_c + 2
			self.grab_cut_mask[sh_l[0]:sh_r[0], sh_l[1]:sh_r[1]] = cv2.GC_FGD
			#self.grab_cut_mask[sh[0]//2, sh[1]//2] = cv2.GC_FGD
			# self.grab_cut_mask[0, 0] = cv2.GC_BGD
			#print('gc mask bincount', np.bincount(self.grab_cut_mask.reshape(-1)))

		def gc_init(mode = cv2.GC_INIT_WITH_RECT):
			cv2.grabCut(
				self.photo_crop,
				self.grab_cut_mask,
				tuple(np.concatenate([self.roi_tl, self.roi_br-self.roi_tl], axis=0)),
				self.grab_cut_state[0:1],
				self.grab_cut_state[1:2],
				self.GRAB_CUT_NUM_ITER, mode,
			)

		try:
			gc_init()
		except cv2.error:
			log.warning('GrabCut failed on initialization - retrying with center pixel marked')
			set_center_pixel_to_foreground()
			gc_init(mode=cv2.GC_INIT_WITH_RECT | cv2.GC_INIT_WITH_MASK)

		# exclude previously existing instances
		if existing_instance_mask_global is not None:
			# we do not do it in the single init step, because if we use the "init with mask" mode
			# grab-cut expects to have BOTH negative and positive samples and crashes on an assert
			#  - but we only have negative samples
			# therefore, we will now perform another step but with the negative samples
			existing_instance_mask_crop = existing_instance_mask_global[self.crop_tl[1]:self.crop_br[1], self.crop_tl[0]:self.crop_br[0]]

			if np.any(existing_instance_mask_crop):
				self.grab_cut_mask[np.where(existing_instance_mask_crop)] = cv2.GC_BGD
				log.debug('Applying mask of existing objects to the new instance, label counts: {nonzero} {bc}'.format(
					nonzero = np.count_nonzero(existing_instance_mask_crop),
					bc = np.bincount(self.grab_cut_mask.reshape(-1)),
				))
				
				try:
					self.grab_cut_update()
				except cv2.error:
					log.warning('GrabCut failed after applying existing object mask - retrying with center pixel marked')
					set_center_pixel_to_foreground()
					self.grab_cut_update()

		self.update_mask()


	def grab_cut_update(self):
		cv2.grabCut(
			self.photo_crop,
			self.grab_cut_mask,
			None,
			self.grab_cut_state[0:1],
			self.grab_cut_state[1:2],
			self.GRAB_CUT_NUM_ITER, cv2.GC_INIT_WITH_MASK,
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

		class_color_bgr = self.semantic_class.color[::-1]
		overlay_crop[self.mask] = np.concatenate([class_color_bgr, [self.ALPHA_CLASS_COLOR]], axis=0)
		overlay_crop[self.contour_where] = np.concatenate([class_color_bgr, [self.ALPHA_CONTOUR]], axis=0)

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
	def from_dict(backend, saved_info, config, photo):

		inst = GrabCutInstance(
			backend,
			saved_info['id'], config.classes_by_id[saved_info['cls']], photo,
			np.array(saved_info['crop_rect']), np.array(saved_info['roi_rect']),
		)
		return inst

		# self.depth_index += change
		# log.debug(f'Depth index +{change} is now {self.depth_index}')
		# self.backend.reindex(self, new_index)
		# self.update_qt_info()

	# Expose to Qt
	infoChanged = Signal()
	info = Property("QVariant", notify=infoChanged)
	@info.getter
	def getInfo(self):
		return self.qt_info

	def update_qt_info(self):
		self.qt_info = dict(
			id = self.id,
			name = f'{self.id} {self.semantic_class.name} {self.depth_index}',
			cls = self.semantic_class.to_dict(),
			x = float(self.crop_tl[0] + self.roi_tl[0]),
			y = float(self.crop_tl[1] + self.roi_tl[1]),
			width = float(self.roi_br[0] - self.roi_tl[0]),
			height = float(self.roi_br[1] - self.roi_tl[1]),
			depth_index = self.depth_index,
		)
		self.infoChanged.emit()

	deleted = Signal()


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
		#print(f'byte view {self.image_view.shape} {self.image_view.dtype}')

		self.image_view[:] = 0

	def requestImage(self, id, size, requestedSize):
		#log.debug(f'requested img name={id} size={size} reqSize={requestedSize}')
		return self.image_qt


class LabelConfig:
	class SemanticClass:
		def __init__(self, id, name, color):
			self.id = id
			self.name = name
			self.color = self.convert_color(color)

		def __repr__(self):
			return f'{self.id}_{self.name}'

		def to_dict(self):
			return {'id': self.id, 'name': self.name, 'color': QColor(*self.color)}

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

	def __init__(self):
		self.set_classes([
			self.SemanticClass(2, 'anomaly', 'orangered'),
		])

	def set_classes(self, classes):
		self.classes = classes
		self.classes_by_id = {cls.id: cls for cls in classes}

	def load_from_path(self, path):
		with Path(path).open('r') as f_in:
			content_json = json.load(f_in)

		self.set_classes([
			self.SemanticClass(cls_json['id'], cls_json['name'], cls_json['color'])
			for cls_json in content_json['classes']
		])

	def to_simple_objects(self):
		return [cls.to_dict() for cls in self.classes]


class LabelBackend(QObject):


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

		self.instances = []
		self.instances_by_id = {}

		self.image_provider = LabelOverlayImageProvider()
		self.config = LabelConfig()

	# Semantic classes
	def load_config(self, cfg_path):
		if cfg_path.is_file():
			self.config.load_from_path(cfg_path)
		else:
			log.error(f'Config path {cfg_path} is not a file')

	@staticmethod
	def load_photo(img_path):
		""" Load image and ensure it is 8bit RGB """
		img_data = imageio.imread(img_path)

		# 8 bit
		img_data = img_data.astype(np.uint8)

		# ensure that is has 3 channels
		if img_data.shape.__len__() == 2: # 2D grayscale
			img_data = np.broadcast_to(img_data[:, :, None], img_data.shape + (3,))

		if img_data.shape[2] == 4: #RGBA
			img_data = img_data[:, :, :3]

		return img_data

	def set_image_path(self, img_path):
		log.info(f'Loading image {img_path}')

		# Load new image
		self.img_path = Path(img_path)
		self.photo = self.load_photo(self.img_path)
		self.resolution = np.array(self.photo.shape[:2][::-1])
		self.image_provider.init_image(self.resolution)
		self.overlay_data = self.image_provider.image_view

		# Clear instances
		for old_inst in self.instances:
			old_inst.deleted.emit()
		self.instances = []
		self.instances_by_id = {}

		# Load state
		data_dir = self.img_path.with_suffix('.labels')
		if data_dir.is_dir():
			log.info(f'Loading saved state from {data_dir}')
			self.load(data_dir)

		self.next_instance_id = int(np.max([0] + [inst.id for inst in self.instances]) + 1)
		self.instances_by_id = {inst.id: inst for inst in self.instances}
		self.instance_selected = None
		self.overlay_refresh_after_selection_change()

	@Slot(QUrl)
	def set_image(self, img_url : QUrl):
		try: # this has to finish, we don't want to break UI interaction
			self.set_image_path(img_url.toLocalFile())
		except Exception as e:
			log.exception('Exception in set_image')

	@Slot(int, QPointF)
	def paint_circle(self, label_to_paint : int, center : QPointF):
		try: # this has to finish, we don't want to break UI interaction

			if self.instance_selected:
				center_pt = np.rint(center.toTuple()).astype(dtype=np.int)

				self.instance_selected.paint_circle(label_to_paint, center_pt)
				self.instance_selected.grab_cut_update()
				self.overlay_refresh_after_edit()
			else:
				log.info('paint_circle: no instance is selected')

		except Exception as e:
			log.exception('Exception in paint_circle')

	@Slot(int, QJSValue)
	def paint_polygon(self, label_to_paint : int, points : QJSValue):
		try:  # this has to finish, we don't want to break UI interaction

			if self.instance_selected:
				points = np.array([p.toTuple() for p in points.toVariant()])

				self.instance_selected.paint_polygon(label_to_paint, points)
				self.instance_selected.grab_cut_update()
				self.overlay_refresh_after_edit()
			else:
				log.info('paint_polygon: no instance is selected')

		except Exception as e:
			log.exception('Exception in paint_polygon')

	def overlay_refresh_after_selection_change(self):
		if self.instance_selected:

			self.overlay_data[:] = (0, 0, 0, 128)
			self.instance_selected.draw_overlay_edit_interface(self.overlay_data)

		else:
			self.overlay_data[:] = 0

			# draw with depth in mind
			for inst in reversed(self.instances_by_depthindex()):
				inst.draw_overlay_contour(self.overlay_data)

		self.overlayUpdated.emit()
		self.selectedUpdate.emit()

	def overlay_refresh_after_edit(self):
		if self.instance_selected:
			self.instance_selected.draw_overlay_edit_interface(self.overlay_data)
			self.overlayUpdated.emit()
		else:
			log.info('overlay_refresh_after_edit but instance_selected is null')

	def depth_index_new(self):
		return max((inst.depth_index for inst in self.instances), default=0) + 1

	def instances_by_depthindex(self):
		instances_by_depthindex = self.instances.copy()
		instances_by_depthindex.sort(key=attrgetter('depth_index'))
		return instances_by_depthindex

	@Slot(int)
	def select_instance(self, instance_id : int):
		self.instance_selected = self.instances_by_id.get(instance_id, None)
		self.overlay_refresh_after_selection_change()

	@Slot(QRectF, int)
	def new_instance(self, roi_rect_qt : QRectF, sem_class_id : int):
		try: # this has to finish, we don't want to break UI interaction
			roi_rect = np.rint(self.qml_rect_to_np(roi_rect_qt)).astype(np.int)
			sem_class = self.config.classes_by_id.get(sem_class_id, self.config.classes[0])

			margin = 32
			crop_rect = np.array([
				np.maximum(roi_rect[0] - margin, 0),
				np.minimum(roi_rect[1] + margin, self.resolution),
			])

			# automatically mark existing instances as excluded from the new instance
			existing_instance_mask = np.zeros(tuple(self.resolution[::-1]), dtype=np.uint8)
			for inst in self.instances:
				inst.draw_mask(existing_instance_mask, 1)

			instance = GrabCutInstance(self, self.next_instance_id, sem_class, self.photo, crop_rect, roi_rect)
			self.next_instance_id += 1

			instance.grab_cut_init(existing_instance_mask)

			self.instances.append(instance)
			self.instances_by_id[instance.id] = instance
			self.select_instance(instance.id)

			self.instanceAdded.emit(instance)

		except Exception as e:
			log.exception('Exception in new_instance')

	@Slot(int, int)
	def set_instance_class(self, instance_id : int, class_id : int):
		try:  # this has to finish, we don't want to break UI interaction
			inst = self.instances_by_id[instance_id]
			cls = self.config.classes_by_id[class_id]

			inst.semantic_class = cls
			inst.update_qt_info()
			self.overlay_refresh_after_selection_change()

		except Exception as e:
			log.exception('Exception in set_instance_class')

	@Slot(int)
	def delete_instance(self, instance_id : int):
		try:  # this has to finish, we don't want to break UI interaction
			inst = self.instances_by_id[instance_id]

			if self.instance_selected == inst:
				self.select_instance(0)

			del self.instances_by_id[instance_id]
			self.instances.remove(inst)

			inst.deleted.emit()
			self.overlay_refresh_after_selection_change()

		except Exception as e:
			log.exception('Exception in delete_instance')

	@Slot(int, int)
	def change_instance_depth(self, instance_id : int, change : int):
		try:  # this has to finish, we don't want to break UI interaction
			
			instance = self.instances_by_id[instance_id]
			# -1 because array is 0 indexed but depth is 1-indexed
			requested_index = max(0, instance.depth_index - 1 + change)

			instances_by_depthindex = self.instances_by_depthindex()
			instances_by_depthindex.remove(instance)
			instances_by_depthindex.insert(requested_index, instance)

			#log.debug(f'Depth: moving inst {instance.id} to {requested_index}')

			for i, inst in enumerate(instances_by_depthindex):
				new_depth_index = i+1

				if new_depth_index != inst.depth_index:
					#log.debug(f'Inst {inst.id} depth change: {inst.depth_index} -> {new_depth_index}')
					inst.depth_index = new_depth_index
					inst.update_qt_info()

		except Exception as e:
			log.exception(f'Exception in change_instance_depth, args: {instance_id}, {change}')

	@Slot()
	def save(self):
		try:  # this has to finish, we don't want to break UI interaction
			log.info(f'save {self.img_path}')

			# outputs
			sem_map = np.zeros(tuple(self.resolution[::-1]), dtype=np.uint8)
			sem_colorimg = np.zeros(tuple(self.resolution[::-1]) + (3,), dtype=np.uint8)
			inst_map = np.zeros(tuple(self.resolution[::-1]), dtype=np.uint8)

			# draw the instance list, using depth_index as label
			for inst_label_min1, inst in reversed(enumerate(self.instances_by_depthindex())):
				inst.draw_mask(sem_map)
				inst.draw_mask(sem_colorimg, inst.semantic_class.color)
				inst.draw_mask(inst_map, inst_label_min1+1)

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
		except Exception as e:
			log.exception('Exception in save')

	def load(self, in_dir):
		with (in_dir / 'index.json').open('r') as f_in:
			json_data = json.load(f_in)

		self.instances = [
			GrabCutInstance.from_dict(self, inst_data, self.config, self.photo)
			for inst_data in json_data['instances']
		]

		for inst in self.instances:
			inst.load_from_dir(in_dir)
			self.instanceAdded.emit(inst)

	# Expose to Qt
	overlayUpdated = Signal()
	instanceAdded = Signal(QObject)

	classesUpdated = Signal()
	classes = Property('QVariant', notify=classesUpdated)
	@classes.getter
	def get_classes(self):
		return self.config.to_simple_objects()

	@Slot(result='QVariant')
	def get_instances(self):
		return self.instances

	selectedUpdate = Signal()
	selected = Property(QObject, attrgetter('instance_selected'), notify=selectedUpdate)

class QtUtils(QObject):

	@Slot(QUrl, result=str)
	def url_parent_directory(self, url : QUrl):
		path = Path(url.toLocalFile())
		parent_dir = path.parent
		return str(parent_dir)

	@Slot(str, result=str)
	def shortcut_text(self, name_or_enum : str):
		# shortcut is always cast to string
		# but somtimes it is a key str "PgUp" and sometimes the QKeySequence.StandardKey enum value

		# https://doc.qt.io/qtforpython/PySide2/QtGui/QKeySequence.html
		# A QApplication instance must have been constructed before a QKeySequence is created; otherwise, your application may crash.

		try:
			enum_val = int(name_or_enum)
			ks = QKeySequence(QKeySequence.StandardKey(enum_val))
		except ValueError:
			ks = QKeySequence(name_or_enum)

		text = ks.toString(QKeySequence.NativeText)
		return f' [{text}]' if text else ''
