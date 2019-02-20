import QtQuick 2.11
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.11
import QtQuick.Dialogs 1.1
import QtQuick.Shapes 1.11
import QtQuick.Window 2.2
import QtQuick.Controls.Universal 2.12


ApplicationWindow {
	id: window
	title: "Label Grab"
	visible: true
	width: Screen.width
	height: Screen.height

	Universal.theme: Universal.Dark
	Universal.accent: Universal.Violet

	menuBar: MenuBar {
		Menu {
			title: qsTr("&File")
			Action { text: qsTr("&Open..."); shortcut: StandardKey.Open; icon.name: "file-open"
				onTriggered: openFileDialog.open();
			}
			Action { text: qsTr("&Save"); shortcut: StandardKey.Save; icon.name: "file-save";
				onTriggered: backend.save();
			}

			MenuSeparator { }
			Action { text: qsTr("&Quit"); icon.name: "quit"; onTriggered: Qt.quit() }
		}
//		Menu {
//			title: qsTr("&Edit")

//			//Action { text: qsTr("&New instance"); shortcut: StandardKey.New; icon.name: "edit-new" }

//			//Action { text: qsTr("Undo"); icon.name: "edit-undo"; shortcut: StandardKey.Undo }
//			//Action { text: qsTr("Redo"); icon.name: "edit-redo"; shortcut: StandardKey.Redo }
//		}
		Menu {
			title: qsTr("&View")

			Action {
				id: actionToggleOverlay
				text: qsTr("Toggle overlay") + ' [' + this.shortcut + ']'
				shortcut: "Tab"
				onTriggered: {
					imageOverlay.visible = !imageOverlay.visible;
				}
			}
		}
	}

	FileDialog {
		id: openFileDialog
		title: "Please choose a file"
		folder: "../../../example_data"

		onAccepted: {
			console.log("You chose: " + openFileDialog.fileUrls);
			backend.set_image(openFileDialog.fileUrl);
			imagePhoto.source = openFileDialog.fileUrl;

			imageContainer.resetTransform();
		}
		onRejected: {
			console.log("Canceled")
		}
	}

	header: ToolBar {
		RowLayout {
			id: headerRowLayout
			//anchors.fill: parent
			Layout.alignment: Qt.AlignLeft
			spacing: 0

			ToolButton {
				text: actionToggleOverlay.text; action: actionToggleOverlay
				background: Rectangle {
					color: imageOverlay.visible ? "transparent" : "orangered"
				}
			}

			Component {
				id: classButton

				ToolButton {
					property var cls
					property var hotkey
					property bool isCurrent: {
						if(! backend.selected ) {
							return false;
						}
						return backend.selected.info.cls.id === cls.id;
					}

					text: cls.name + ((hotkey !== null) ? (" [" + hotkey + "]")  : "")

					background: Rectangle {
						color: "transparent"
						border.color: cls.color
						border.width: isCurrent ? 5 : 1
					}

					action: Action {
						shortcut: hotkey
						onTriggered: {
							const clsid = cls.id;

							if(backend.selected !== null) {
								backend.set_instance_class(backend.selected.info.id, clsid);
							}
							viewportMouse.last_used_class_id = clsid;
						}
					}
				}
			}

//			Item {
//				Layout.row: 100
//				Layout.column: 100
//				Layout.fillWidth: true
//			}
		}

		Component.onCompleted: {
			const classes = backend.classes;
			const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"];

			if(classes.length > 0) {
				viewportMouse.last_used_class_id = classes[0].id;
			}

			for (var i = 0; i < classes.length; i++) {
				classButton.createObject(headerRowLayout, {
					cls: classes[i],
					hotkey: (i < keys.length) ? keys[i] : null,
				});
			}
		}
	}

	RowLayout {
		anchors.fill: parent
		spacing: 5

		Rectangle {
			id: viewport

			Layout.fillWidth: true
			Layout.fillHeight: true

			color: '#2a2a2a'

			Item {
				id: imageContainer

				// initially place it in the middle
				x: parent.width * 0.5
				y: parent.height * 0.5

				transform: [imageTranslation, imageScale]

				Scale {
					id: imageScale
					property real value: 1.0
					xScale: value
					yScale: value
				}

				Translate {
					id: imageTranslation
				}

				function resetTransform() {
					imageScale.value = Math.min(parent.width / (imagePhoto.implicitWidth + 32), parent.height / (imagePhoto.implicitHeight + 32));
					imageTranslation.x = 0;
					imageTranslation.y = 0;
				}

				Image {
					id: imagePhoto
					source: "images/test.jpg"

					anchors.horizontalCenter: imageContainer.horizontalCenter
					anchors.verticalCenter: imageContainer.verticalCenter
				}

				Image {
					id: imageOverlay

					source: "image://backend/overlay"
					cache: false
					smooth: false

					anchors.horizontalCenter: imageContainer.horizontalCenter
					anchors.verticalCenter: imageContainer.verticalCenter

					Component.onCompleted: {
						// Listen for updated of the overlay data

						// The only way to refresh is to change the URL
						const base_url = this.source + '#';
						var suffix = 0;

						backend.overlayUpdated.connect(function() {
							imageOverlay.source = base_url + suffix;
							suffix = 1 - suffix;
						})

						imageContainer.resetTransform();
					}

					Shape {
						id: brushPolygon
						visible: false

						Component {
							id: brushPolygonSegmentTemplate
							PathLine {}
						}

						ShapePath {
							id: brushPolygonPath


							strokeWidth: 1
							strokeColor: (viewportMouse.label_to_paint == 0) ? "#F00000" : "#00F000"

	//						strokeStyle: ShapePath.DashLine
	//						dashPattern: [ 1, 2]

							fillColor: (viewportMouse.label_to_paint == 0) ? "#20F00000" : "#2000F000"

							PathLine {
								property point startPoint:  viewportMouse.mapToItem(brushPolygon, viewportMouse.mouseX, viewportMouse.mouseY)

								id: segmentToMouse
								x: startPoint.x
								y: startPoint.y
							}

							PathLine {
								id: segmentToBeginning
								x: brushPolygonPath.startX
								y: brushPolygonPath.startY
							}
						}

						function start_polygon(pt) {
							brushPolygonPath.startX = pt.x;
							brushPolygonPath.startY = pt.y;
							brushPolygonPath.pathElements = [segmentToMouse, segmentToBeginning];
							//brushPolygonPath.pathElements = [segmentToBeginning];
							this.add_point(pt)
						}

						function add_point(pt) {
							const new_segment = brushPolygonSegmentTemplate.createObject(
								brushPolygonPath,
								{'x': pt.x, 'y': pt.y}
							);

							var new_list = [];
							//new_list.pop();
							for(var idx = 0; idx < brushPolygonPath.pathElements.length - 2; idx += 1) {
								new_list.push(brushPolygonPath.pathElements[idx])
							}
							new_list.push(new_segment);
							new_list.push(segmentToMouse);
							new_list.push(segmentToBeginning);

							brushPolygonPath.pathElements = new_list;
						}

						function finish() {
							brushPolygonPath.pathElements = [];
						}
					}
				}
			}

			Rectangle{
				id: roiRect
				visible: false
				color: "transparent"
				border.color: "cyan"
				border.width: 3
			}

			MouseArea {
				id: viewportMouse
				property point move_offset
				property point rect_origin
				property point last_polygon_click
				property int label_to_paint: 1
				property var polygon_points: []
				property int last_used_class_id: 1

				anchors.fill: parent
				acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
				hoverEnabled: true

				onWheel: {
					imageScale.value += imageScale.value * wheel.angleDelta.y / 1200;
				}

				onPressed: function(event) {
					//console.log('press', event.button, 'at', event.x, event.y)//, ' img', m_img);

					const m_img = this.mapToItem(imagePhoto, event.x, event.y);

					if(event.button === Qt.MiddleButton || event.modifiers & Qt.ControlModifier || (event.button === Qt.RightButton && !backend.selected)) {
						/*
						Dragging moves the image container to:
							container.pos = container.initial_position + mouse_position_current - mouse_position_at_start
						So we only need to save
							move_offset = container.initial_position - mouse_position_at_start
						and set the position accordingly
							container.pos = move_offset + mouse_position_current
						*/
						const scale_inv = 1./imageScale.value; // the translation is applied before scale, we our offset has to compensate for that
						this.move_offset = Qt.point(imageTranslation.x - scale_inv * event.x, imageTranslation.y - scale_inv * event.y);
						this.state = "move";

					} else {
						if(event.button === Qt.LeftButton) {
							this.label_to_paint = 1;
						}
						else if (event.button === Qt.RightButton) {
							this.label_to_paint = 0;
						}

						if ( event.modifiers & Qt.ShiftModifier ) {
							this.rect_origin = Qt.point(event.x, event.y);
							this.state = "new_instance";
						}
						else if ( event.modifiers & Qt.AltModifier  && backend.selected) {
							backend.paint_circle(this.label_to_paint, m_img);
						}
						else if ( backend.selected ) // draw polygon only if we have a selected instance
						{
							this.polygon_points.length = 0;
							this.polygon_points.push(m_img);
							brushPolygon.start_polygon(m_img);
							this.state = "draw_polygon";
						}
					}
				}

				function cancel_action() {;
					this.state = "";
				}

				function finalize_polygon() {
					console.log("Polygon finished", this.polygon_points);
					backend.paint_polygon(this.label_to_paint, this.polygon_points);
					brushPolygon.finish();
					this.state = "";
				}

				property var key_cancel: function(event) {
					backend.select_instance(0);
				}

				property var key_confirm: function(event) {}

				onExited: cancel_action()

				Shortcut {
					sequence: "Esc"
					onActivated: viewportMouse.key_cancel();
				}

				Shortcut {
					sequence: "Return"
					onActivated: viewportMouse.key_confirm();
				}

				Shortcut {
					sequence: "Del"
					onActivated: {
						if(backend.selected !== null) {
							deleteDialog.instance_info = backend.selected.info;
							deleteDialog.open();
						} else {
							console.log('Delete: no instance selected');
						}
					}
				}

				Dialog {
					id: deleteDialog
					property var instance_info: {name: 'not initialized'}

					title: "Delete instance " + instance_info.name + "?"

					standardButtons: Dialog.Ok | Dialog.Cancel

					onAccepted: backend.delete_instance(instance_info.id);
					onRejected: console.log("Cancel delete")
				}

				states: [
					State{
						name: "move"
						PropertyChanges{
							target: viewportMouse

							onReleased: cancel_action()

							onPositionChanged: function(event) {
								const scale_inv = 1./imageScale.value; // the translation is applied before scale, we our offset has to compensate for that
								imageTranslation.x = this.move_offset.x + event.x*scale_inv;
								imageTranslation.y = this.move_offset.y + event.y*scale_inv;
							}
						}
					},
					State{
						name: "draw_polygon"
						PropertyChanges{
							target: viewportMouse

							onPressed: function(event) {
								if(!( event.x === last_polygon_click.x && event.y === last_polygon_click.y )) {
									last_polygon_click.x = event.x;
									last_polygon_click.y = event.y;
									const m_img = this.mapToItem(imagePhoto, event.x, event.y);
									this.polygon_points.push(m_img);
									brushPolygon.add_point(m_img);
								}
							}
							onDoubleClicked: function(event) {
								this.finalize_polygon();
							}
							key_cancel: function(event) {
								console.log('cancel polygon');
								this.cancel_action();
							}
							key_confirm: function(event) {
								this.finalize_polygon();
							}
						}
						PropertyChanges{
							target: brushPolygon

							visible: true
						}
					},

					State{
						name: "new_instance"
						PropertyChanges {
							target: roiRect
							visible: true
							x: Math.min(viewportMouse.mouseX, viewportMouse.rect_origin.x)
							y: Math.min(viewportMouse.mouseY, viewportMouse.rect_origin.y)
							width: Math.abs(viewportMouse.mouseX - viewportMouse.rect_origin.x)
							height: Math.abs(viewportMouse.mouseY - viewportMouse.rect_origin.y)
						}

						PropertyChanges {
							target: viewportMouse

							onReleased: function(event) {
								console.log('New instance:', this.rect_origin, ' to ', event.x, event.y;

								const re = viewportMouse.mapToItem(imagePhoto,
									Math.min(viewportMouse.mouseX, viewportMouse.rect_origin.x),
									Math.min(viewportMouse.mouseY, viewportMouse.rect_origin.y),
									Math.abs(viewportMouse.mouseX - viewportMouse.rect_origin.x),
									Math.abs(viewportMouse.mouseY - viewportMouse.rect_origin.y),
								);

								backend.new_instance(re, viewportMouse.last_used_class_id);
								this.cancel_action();
							}
						}
					}

				]
			}
		}

		Rectangle {
			id: sidebar

			Layout.preferredWidth: 150
			Layout.fillHeight: true

			color: Universal.foreground
			border.width: 0

			ColumnLayout {
				id: sidebarInstances
				width: parent.width
				//anchors.fill

				Label {
					text: "Instances"
				}

				Component {
					id: sidebarInstanceTemplate

					Button {
						property var instance
						text: instance.info.id + " " + instance.info.cls.name
						Layout.fillWidth: true

						background: Rectangle {
							color: "transparent"
							border.color: instance.info.cls.color
							border.width: 2
						}

						onClicked: {
							backend.select_instance(instance.info.id);
						}

						Component.onCompleted: {
							instance.deleted.connect(function() {
								destroy();
							});
						}
					}
				}
			}

			Component.onCompleted: {
				function on_new_instance(inst) {
					sidebarInstanceTemplate.createObject(sidebarInstances, {
						instance: inst,
					});
				}

				const insts = backend.get_instances();
				for(var idx = 0; idx < insts.length; idx++) {
					on_new_instance(insts[idx]);
				}

				backend.instanceAdded.connect(on_new_instance);
			}
		}
	}
}
