import QtQuick 2.11
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.11

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
				text: 'Tool 1'
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

				Image {
					id: imagePhoto
					source: "resources/test.jpg"

					anchors.horizontalCenter: imageContainer.horizontalCenter
					anchors.verticalCenter: imageContainer.verticalCenter
				}

				Image {
					id: imageOverlay
					source: "image://label_overlay/overlay"

					anchors.horizontalCenter: imageContainer.horizontalCenter
					anchors.verticalCenter: imageContainer.verticalCenter
				}
			}

			MouseArea {
				anchors.fill: parent
				onWheel: {
					if (wheel.modifiers & Qt.ControlModifier) {
						imageContainer.rotation += wheel.angleDelta.y / 120 * 5;
						if (Math.abs(imageContainer.rotation) < 4)
							imageContainer.rotation = 0;
					} else {
						imageContainer.rotation += wheel.angleDelta.x / 120;
						if (Math.abs(imageContainer.rotation) < 0.6)
							imageContainer.rotation = 0;
						var scaleBefore = imageContainer.scale;
						imageContainer.scale += imageContainer.scale * wheel.angleDelta.y / 120 / 10;
					}
				}

				drag.target: imageContainer
			}
		}

		Rectangle {
			id: sidebar

			Layout.preferredWidth: 150
			Layout.fillHeight: true

			color: 'azure'
		}
	}
}
