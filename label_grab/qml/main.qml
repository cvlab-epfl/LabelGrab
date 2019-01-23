import QtQuick 2.11
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.11
import QtQuick.Shapes 1.11

ApplicationWindow {
	id: window
	title: "Label Grab"
	visible: true
	width: 1024; height: 720

	menuBar: MenuBar {
		Menu {
			title: qsTr("&File")
			Action { text: qsTr("&Open..."); shortcut: StandardKey.Open; icon.name: "file-open"}

			MenuSeparator { }
			Action { text: qsTr("&Quit"); icon.name: "quit"; onTriggered: Qt.quit() }
		}
		Menu {
			title: qsTr("&Edit")

			Action { text: qsTr("Undo"); icon.name: "edit-undo"; shortcut: StandardKey.Undo }
			Action { text: qsTr("Redo"); icon.name: "edit-redo"; shortcut: StandardKey.Redo }
		}
	}

	header: ToolBar {
		RowLayout {
			id: headerRowLayout
			anchors.fill: parent
			spacing: 0

			ToolButton {
				text: '+ New Instance'
			}
			ToolButton {
				text: 'Tool 2'
			}

			Item {
				Layout.fillWidth: true
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

				Image {
					id: imagePhoto
					source: "resources/test.jpg"

					anchors.horizontalCenter: imageContainer.horizontalCenter
					anchors.verticalCenter: imageContainer.verticalCenter
				}

				Image {
					id: imageOverlay

					source: "image://backend/overlay"
					cache: false

					anchors.horizontalCenter: imageContainer.horizontalCenter
					anchors.verticalCenter: imageContainer.verticalCenter

					Component.onCompleted: {
						// Listen for updated of the overlay data

						// The only way to refresh is to change the URL
						const base_url = this.source + '#';
						var suffix = 0;

						backend.OverlayUpdated.connect(function() {
							imageOverlay.source = base_url + suffix;
							suffix = 1 - suffix;
						})
					}
				}
			}

			Shape {
				id: brush
				x: viewportMouse.mouseX
				y: viewportMouse.mouseY

				property real radius: 5 * imageContainer.scale

				//				x: parent.width * 0.5
				//				y: parent.height * 0.5

				ShapePath {
					strokeWidth: 1
					strokeColor: "red"
					strokeStyle: ShapePath.DashLine
					dashPattern: [ 1, 2]

					fillColor: "transparent"

					startX: -brush.radius; startY: 0
					PathArc {
						x: brush.radius; y: 0
						radiusX: brush.radius; radiusY: brush.radius
					}
					PathArc {
						x: -brush.radius; y: 0
						radiusX: brush.radius; radiusY: brush.radius
					}
				}
			}

			Rectangle{
				id: roiRect
				visible: false
				color: "#0055ff80"
				border.color: "red"
				border.width: 3
			}

			MouseArea {
				id: viewportMouse
				property point move_offset
				property point rect_origin

				anchors.fill: parent
				acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
				hoverEnabled: true

				onWheel: {
					imageContainer.scale += imageContainer.scale * wheel.angleDelta.y / 120 / 10;
				}

				onPressed: function(event) {
					console.log('press', event.button, 'at', event.x, event.y)//, ' img', m_img);

					if(event.button === Qt.MiddleButton) {
						/*
						Dragging moves the image container to:
							container.pos = container.initial_position + mouse_position_current - mouse_position_at_start
						So we only need to save
							move_offset = container.initial_position - mouse_position_at_start
						and set the position accordingly
							container.pos = move_offset + mouse_position_current
						*/
						this.move_offset = Qt.point(imageContainer.x - event.x, imageContainer.y - event.y);
						this.state = "move";

					} else {
						if ( event.modifiers & Qt.ShiftModifier ) {
							this.rect_origin = Qt.point(event.x, event.y)
							this.state = "rect"
						}
						else
						{
							const m_img = this.mapToItem(imagePhoto, event.x, event.y);

							var label_to_paint = 0;
							if(event.button === Qt.LeftButton) {
								label_to_paint = 1;
							}
							else if (event.button === Qt.RightButton) {
								label_to_paint = 0;
							}

							backend.paint_circle(label_to_paint, m_img);
						}
					}
				}

				function cancel_action() {
					this.state = "";
				}

				onReleased: cancel_action()
				onExited: cancel_action()

				states: [
					State{
						name: "move"
						PropertyChanges{
							target: viewportMouse

							onPositionChanged: function(event) {
								imageContainer.x = this.move_offset.x + event.x;
								imageContainer.y = this.move_offset.y + event.y;
							}
						}
						StateChangeScript {
							script: {
								console.log('entered state')
							}
						}
					},
					State{
						name: "rect"
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
								console.log('Set roi', this.rect_origin, ' to ', event.x, event.y, Qt.rect);

								const re = viewportMouse.mapToItem(imagePhoto,
									Math.min(viewportMouse.mouseX, viewportMouse.rect_origin.x),
									Math.min(viewportMouse.mouseY, viewportMouse.rect_origin.y),
									Math.abs(viewportMouse.mouseX - viewportMouse.rect_origin.x),
									Math.abs(viewportMouse.mouseY - viewportMouse.rect_origin.y),
								);

								backend.set_roi(re);
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

			color: 'azure'

			ColumnLayout {
				anchors.fill: parent
				spacing: 5

				ListModel {
					id: instanceListModel

					ListElement {
						name: "Apple"
						num: 1
					}
				}

				Component {
					id: instanceListTemplate
					Row {
						spacing: 5
						Text { text: name }
						Text { text: '$' + num }
					}
				}

				ListView {
					//anchors.fill: parent
					//model: instanceListModel
					model: backend.instanceListModel
					delegate: instanceListTemplate
				}

				Component.onCompleted: {
					//console.log('rowCount', backend.instanceListModel.rowCount());
					//console.log('data', backend.instanceListModel.data(2));
					//backend.use_instance_list(instanceListModel);

					//console.log('model[0]', instanceListModel.get(0));
				}
			}
		}
	}
}
