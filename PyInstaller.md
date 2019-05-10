
# Single executable with PyInstaller


## Install PyInstaller

We need to install PyInstaller from an unmerged oull request which fixes an error with PySide2:

<https://github.com/sjackso/pyinstaller/tree/fix_3689>

Maybe it will be merged into release some day.

## Build

We need to include the qml and config resources.

One file:
```
pyinstaller main.py --name label-grab-ex --onefile --add-data label_grab/resources/:label_grab/resources
```

Directory:
```
pyinstaller main.py --name label-grab --add-data label_grab/resources/:label_grab/resources
```

Windows for some reason wants `;` instead of `:`
```
pyinstaller main.py --name label-grab-win --onefile --add-data "label_grab/resources/;label_grab/resources"
pyinstaller main.py --name label-grab-win --add-data "label_grab/resources/;label_grab/resources"
```

## AppImage

* Install `appimagetool` from <https://github.com/AppImage/AppImageKit/releases>.

```
pyinstaller main.py --name label-grab --add-data label_grab/resources/:label_grab/resources
cd dist/label-grab
ln -s label-grab AppRun # The entry point for AppImage is AppRun
ln -s label_grab/resources/label-grab.desktop .
ln -s label_grab/resources/label-grab-icon.svg . # The icon has to be in the top directory
cd ..
$ARCH="x86_64"
appimagetool label-grab
```


