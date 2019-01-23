import QtQuick 2.11
import QtQuick.Controls 2.5

Rectangle{
	property var instanceData

	id: instanceRect
	visible: true
	color: "#0055ff80"
	border.color: "green"
	border.width: 3

	z: 1

	width: 100
	height: 100

	Component.onCompleted: {
		console.log('create instance rect', instanceData, instanceData.x, instanceData.y)
		this.x = instanceData.x;
		this.y = instanceData.y;
		this.width = instanceData.width;
		this.height = instanceData.height;
	}
}

//Component{
//	id: instanceRectTemplate


//}
