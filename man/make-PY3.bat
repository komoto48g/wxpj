@echo off

rem: Update PY3* packages (py required)
py -m pip install -U pip
py -m pip install scipy opencv-python pillow matplotlib wxpython
py -m pip install pywin32 flake8 httplib2
py -m pip install -U mwxlib

rem: Install PyJEM if necessary (Uncomment the following line)
rem: py -3.5 -m pip install PyJEM-1.0.2.1143.zip

rem: Update wxpj-master packages (git required)
rem: rm -rf wxpj
git clone https://github.com/komoto48g/wxpj.git
