@echo off

:rem: Update PY35 packages (py required)
py -3.5 -m pip install -U pip
py -3.5 -m pip install scipy opencv-python==3.4.5.20 pillow matplotlib wxpython
py -3.5 -m pip install pywin32 openpyxl flake8 httplib2
py -3.5 -m pip install -U mwxlib

:rem: Update wxpj packages (git required)
rm -rf wxpj
rm -rf wxpj-aero
git clone https://github.com/komoto48g/wxpj.git
git clone https://github.com/komoto48g/wxpj-aero.git

:rem: Install PyJEM if necessary
:rem: If you don't need it, delete the following line
py -3.5 -m pip install PyJEM-1.0.2.1143.zip
