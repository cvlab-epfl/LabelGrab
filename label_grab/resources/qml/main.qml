import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.11
import QtQuick.Dialogs 1.1
import QtQuick.Shapes 1.11
import QtQuick.Window 2.2

import "label_grab_components"

ApplicationWindow {
	id: window
	title: "Label Grab"
	
	visibility: Window.Maximized
	width: Screen.width
	height: Screen.height

	// https://doc.qt.io/qt-5/qtquickcontrols2-fusion.html
	palette.window: "black"
	palette.windowText: "white"
	palette.text: "white"
	palette.base: "dimgray"
	palette.highlight: "darkorange"
	palette.highlightedText: "black"
	palette.button: "dimgray"
	palette.buttonText: "white"

	function modify_depth_index(relative) {
		if(backend.selected !== null) {
			backend.change_instance_depth(backend.selected.info.id, relative)
		} else {
			console.log('Raise/lower: no instance selected');
		}
	}

	StandardPathsProvider {
		id: pathsProvider
	}

	menuBar: MenuBar {
		Menu {
			title: qsTr("&File")
			Action { 
				text: qsTr("Open..." ) + utils.shortcut_text(this.shortcut)
				icon.name: "file-open"
				shortcut: StandardKey.Open
				onTriggered: openFileDialog.open();
			}
			Action { 
				text: qsTr("Save")  + utils.shortcut_text(this.shortcut) 
				icon.name: "file-save"
				shortcut: StandardKey.Save
				onTriggered: function() { 
					const save_success = backend.save();
					if(save_success) {
						notification.show('Saved ' + backend.get_image_path())
					} else {
						notification.show_color('Failed to save ' + backend.get_image_path(), 'red')
					}
				}
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
				text: qsTr("Toggle overlay") + utils.shortcut_text(this.shortcut)
				shortcut: "Tab"
				onTriggered: {
					viewport.overlayVisible = !viewport.overlayVisible;
				}
			}
		}

		Menu {
			title: qsTr("&Instance")
			
			Action {
				id: actionDelete
				text: qsTr("Delete") + utils.shortcut_text(this.shortcut)
				shortcut: "Del"
				onTriggered: this.action_delete()

				function action_delete() {
					if(backend.selected !== null) {
						deleteDialog.instance_info = backend.selected.info;
						deleteDialog.open();
					} else {
						console.log('Delete: no instance selected');
					}
				}
			}
			// mac does not have delete key
			Shortcut {sequence: "Backspace"; onActivated: actionDelete.action_delete()}

			MenuSeparator { }

			Action {
				text: qsTr("Raise instance") + utils.shortcut_text(this.shortcut)
				shortcut: "PgUp"
				onTriggered: modify_depth_index(-1)
			}
			Action {
				text: qsTr("Lower instance") + utils.shortcut_text(this.shortcut)
				shortcut: "PgDown"
				onTriggered: modify_depth_index(+1)
			}
		}
	}

	FileDialog {
		id: openFileDialog
		title: "Please choose a file"
		selectExisting: true
		selectFolder: false
		selectMultiple: false
		folder: pathsProvider.standardPaths.writableLocation(pathsProvider.standardPaths.DocumentsLocation)

		onAccepted: {
			console.log("You chose: " + this.fileUrls);
			this.folder = utils.url_parent_directory(this.fileUrl);		
			const load_success = backend.set_image(this.fileUrl);

			if(load_success) {
				viewport.imageSource = this.fileUrl;
				viewport.resetTransform();
				notification.show('Loaded ' + this.fileUrl)
			} else {
				notification.show_color('Failed to load ' + this.fileUrl, "red")
			}
		}
		onRejected: {
			console.log("Canceled")
		}
	}

	Dialog {
		id: deleteDialog
		property var instance_info: {name: 'not initialized'}

		title: "Delete instance " + instance_info.name + "?"
		modal: true
		standardButtons: Dialog.Ok | Dialog.Cancel
		x: (parent.width - width) * 0.5 
		y: (parent.height - height) * 0.5
		// width: 640
        // height: 320
		//anchors.horizontalCenter: parent.horizontalCenter

		onAccepted: backend.delete_instance(instance_info.id);
		onRejected: console.log("Cancel delete")
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
		id: vpcont

		ImageViewport {
			id: viewport
		}

		InstanceList {
		}
	}

	NotificationBox {
		id: notification
	}
}
