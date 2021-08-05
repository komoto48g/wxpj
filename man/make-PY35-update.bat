@echo off

rem: Update PY35 packages (py required)
py -3.5 -m pip install -U mwxlib

rem: Update wxpj packages (git required)
cd wxpj
git pull https://github.com/komoto48g/wxpj.git
cd ..

rem: Update wxpj aero packages (git required)
cd wxpj-aero
git pull https://github.com/komoto48g/wxpj-aero.git
cd ..
