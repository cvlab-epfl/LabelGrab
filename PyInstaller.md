
# Single executable with PyInstaller


## Install PyInstaller

We need to install PyInstaller from an unmerged oull request which fixes an error with PySide2:

<https://github.com/sjackso/pyinstaller/tree/fix_3689>

Maybe it will be merged into release some day.

## Build

We need to include the qml and config resources.

One file (but can do better single-file program with appimage):
```bash
pyinstaller main.py --name label-grab-exe --onefile --add-data label_grab/resources/:label_grab/resources
```

Directory:
```bash
pyinstaller main.py --name label-grab --add-data label_grab/resources/:label_grab/resources
```

Windows for some reason wants `;` instead of `:`
```bash
# single executable
pyinstaller main.py --name label-grab-win --onefile --add-data "label_grab/resources/;label_grab/resources"
# directory
pyinstaller main.py --name label-grab-win --add-data "label_grab/resources/;label_grab/resources"
```

## AppImage

* Install `appimagetool` from <https://github.com/AppImage/AppImageKit/releases>.

```bash
pyinstaller main.py --name label-grab --add-data label_grab/resources/:label_grab/resources
cd dist/label-grab
ln -s label-grab AppRun # The entry point for AppImage is AppRun
ln -s label_grab/resources/label-grab.desktop .
ln -s label_grab/resources/label-grab-icon.svg . # The icon has to be in the top directory
cd ..
$ARCH="x86_64"
appimagetool label-grab
mv Label_Grab-x86_64.AppImage label-grab.AppImage
```


