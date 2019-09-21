
# Single executable with PyInstaller


## Install PyInstaller

```bash
pip install pyinstaller
```

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
# prepare Windows icon
magick label_grab/resources/label-grab-icon.svg -define icon:auto-resize=64,48,32,16 -background none build/label-grab-icon.ico
# single executable
pyinstaller main.py --name label-grab-win --add-data "label_grab/resources/;label_grab/resources" --icon build/label-grab-icon.ico --onefile
# directory
pyinstaller main.py --name label-grab-win --add-data "label_grab/resources/;label_grab/resources" --icon build/label-grab-icon.ico
```

## AppImage
For Linux, turn the directory into a single executable using [AppImage](https://appimage.org/).

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


