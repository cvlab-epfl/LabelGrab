import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.11

Rectangle {
	id: sidebar

	Layout.preferredWidth: 150
	Layout.fillHeight: true

	// color: Universal.background
	border.width: 0

	color: palette.window

	GridLayout {
		// Needs to be GridLayout because ColumnLayout does not respect child's Layout.row property for ordering
		id: sidebarInstances
		width: parent.width

		columns: 1
		rows: 10

		Label {
			text: "Instances"
			Layout.row: 0
			Layout.column: 0
		}

		Component {
			id: sidebarInstanceTemplate

			Button {
				property var instance
				text: instance ? (instance.info.cls.name  + " " + instance.info.id) : "NULL"

				Layout.fillWidth: true
				Layout.row: instance.info.depth_index
				Layout.column: 0

				background: Rectangle {
					color: "transparent"
					border.color: instance ? (instance.info.cls.color) : "red"
					border.width: (instance === backend.selected) ? 4 : 2
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
