
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


