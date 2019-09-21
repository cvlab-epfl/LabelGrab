import QtQuick 2.12
import Qt.labs.platform 1.1

/*
Provides StandardPaths, for finding user's home directory etc.

It imported from Qt.labs.platform, if this import were in main.qml, it would for some reason break the Dialog.
(dialog would not have its buttons!)
Therefore we isolate this import in this file here
*/

QtObject {
	property var standardPaths: StandardPaths
}
