import QtQuick 2.12
import QtQuick.Controls 2.5

Rectangle {
	id: notification
	property real timeVisible: 1.5
	property var defaultColor: 'green'
	visible: false

	width: childrenRect.width
	height: childrenRect.height
	anchors.left: parent.left;
	anchors.leftMargin: 20
	anchors.bottom: parent.bottom;
	anchors.bottomMargin: 20

	color: palette.window
	border.width: 2

	Label {
		id: notificationText
		text: "Noti"
		padding: 8
	}

	Timer {
		id: notificationDisappearTimer
		interval: notification.timeVisible * 1000 
		running: false
		repeat: false
		onTriggered: notification.visible = false
	}

	function show(text) {
		this.show_color(text, this.defaultColor)
	}
	function show_color(text, color) {
		notificationText.text = text
		notification.visible = true
		notification.border.color = color;
		notificationDisappearTimer.restart()
	}
}
