@echo off

rem: Update PY35 packages (py required)
py -3.5 -m pip install -U pip
py -3.5 -m pip install scipy==1.2.3 opencv-python==3.4.5.20 pillow matplotlib wxpython
py -3.5 -m pip install pywin32 openpyxl flake8 httplib2 mwxlib

ls PyJEM-*|tail -1|xargs py -3.5 -m pip install

rem: Update wxpj packages (git required)
git clone https://github.com/komoto48g/wxpj.git
git clone https://github.com/komoto48g/wxpj-aero.git
