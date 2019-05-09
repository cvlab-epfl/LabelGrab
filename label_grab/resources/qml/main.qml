import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.11
import QtQuick.Dialogs 1.1
import QtQuick.Shapes 1.11
import QtQuick.Window 2.2
import QtQuick.Controls.Universal 2.12

import "label_grab_components"

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
					viewport.overlayVisible = !viewport.overlayVisible;
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
					color: viewport.overlayVisible ? "transparent" : "orangered"
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
							viewport.last_used_class_id = clsid;
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
				viewport.last_used_class_id = classes[0].id;
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

		ImageViewport {
			id: viewport
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
