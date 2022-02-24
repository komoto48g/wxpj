# wxpj

A package for Image analysis and TEM control


## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

私の環境では以下のバージョンで動作しています．
```
<Python 3.8.6 (tags/v3.8.6:db45529, Sep 23 2020, 15:52:53) [MSC v.1927 64 bit (AMD64)]>
  wx.version(selected) 4.1.1 msw (phoenix) wxWidgets 3.1.5
  scipy/numpy version 1.6.0/1.20.1
  matplotlib version 3.4.2
  Image version 8.1.0
  cv2 version 4.5.1
  mwx 0.40
```

![setup](man/image/net.png)

### Prerequisites

***Don't use Anaconda because wxPython cannot be installed.***

* [Python 3.5.4 for Windows](https://www.python.org/downloads/release/python-354/)  
    if you will use PyJEM, this version is required.

* [Python 3.8.6 for Windows](https://www.python.org/downloads/release/python-386/)  
    if you don't use PyJEM, this version is recommended.

* [Git for Windows](https://git-scm.com/)  
    required to pip-install the latest modules from GitHub.

* PyJEM-*.zip (option)  
    The PyJEM package is optional. Required when operating the TEM.


### Installing

Create a workspace to install.

1. Prepare the workspace directory as follows.
```
<your-workdir>
    ├ make-py35.bat (batch file for installation)
    ├ PyJEM-1.0.2.1143.zip (PyJEM package if needed)
    ├ pJ.cmd (batch file for startup)
    └ siteinit.py (initial setting)
```
2. Install Python packages (from pypi) using batch files  

    <details>
      <summary>To install PY35 w/ PyJEM </summary>

    ```
    py -3.5 -m pip install -U pip
    py -3.5 -m pip install scipy opencv-python==3.4.5.20 pillow matplotlib wxpython
    py -3.5 -m pip install pywin32 openpyxl flake8 httplib2
    py -3.5 -m pip install -U mwxlib
    py -3.5 -m pip install PyJEM-1.0.2.1143.zip
    git clone https://github.com/komoto48g/wxpj.git
    ```
    [make-py35.bat](man/make-PY35.bat) file.
    </details>

    <details>
      <summary>To install PY38 (+later) w/o PyJEM</summary>

    ```
    py -m pip install -U pip
    py -m pip install scipy opencv-python pillow matplotlib wxpython
    py -m pip install pywin32 flake8 httplib2
    py -m pip install -U mwxlib
	git clone https://github.com/komoto48g/wxpj.git
    ```
    [make-py3.bat](man/make-PY3.bat) file.
    </details>

#### Note (for internal use only)

- 社内からインストールする場合プロキシが見つからない為に失敗するかもしれません．
  その場合はまず次の設定を行ってください
```
set HTTPS_PROXY=http://i-net.jeol.co.jp:80
set HTTP_PROXY=http://i-net.jeol.co.jp:80
```


### Updating

To update the packages, just run `make-PY3.bat` or `make-PY35.bat` again.
Before updating, delete wxpj directory, or else the latest wxpj will not be cloned.


## How to execute wxpyJemacs

Launch `wxpj/wxpyJemacs.py`.


## How to terminate wxpyJemacs

Press [x] Button.

When you close the program, a popup window will appear asking "Do you want to save session before closing program?".
The session is like a project file, and it roughly saves plugins, parameters, windows layouts, buffers, etc.
Click [OK]. Then, the next time you start the program with the session file, you can start it in the same state as when it was last closed.


## How to restart the session

Suppose the session file is `user.jssn`.
Start from the command prompt:
```
py wxpj/wxpyjemacs.py --pyjem=1 -suser
```
The meanings of the command arguments are:

    --pyjem: Declare using pyjem

        Launch wxpyJemacs with --pyjem=0(=offline), 1(=online), or 2(=online with TEM3)
        The default switch is --pyjem=None, that means no PyJEMs to be involved.
        Please use flag `1` normally.

    -sxxx: Start xxx session

If `.jssn` is associated with the batch file [pJ.cmd](man/pJ.cmd), you can double-click the session file to restart the program easily.


## Deployment

Additional notes about how to deploy this on a live system

    !! PYJEM.TEM3 機能を使用するためには PY <= 3.5 (以下) をインストールしてください．
    !! 別途，TemExternal のインストールが必要です．


## Built With

* [pyDM3reader] - Python DM3 Reader (http://microscopies.med.univ-tours.fr/)

    * Pierre-Ivan Raynal - *Initial work* -  
        http://microscopies.med.univ-tours.fr/  
        https://bitbucket.org/piraynal/pydm3reader/src/master/  
    * Philippe Mallet-Ladeira
    * Greg Jefferis - *Transposition and adaptation of the DM3_Reader ImageJ plug-in* -  
        https://imagejdocu.tudor.lu/plugin/utilities/python_dm3_reader/start

* [pyGatan] - Leginon の Gatan 用スクリプトを PY3 で動くように修正したもの (Contributed by h.iijima)
    * Leginon (https://emg.nysbc.org/redmine/projects/leginon/wiki/Leginon_Homepage)  
    * https://bio3d.colorado.edu/SerialEM/  
    * https://bio3d.colorado.edu/SerialEM/download.html  

<!--
* [pyJeol] (egg only) JEOL legacy TEM package です．主に次のモジュールで構成されます．
    - pyJem: Facade of PyJEM
    - pyJem2: Poor man's PyJEM

* [mwxlib] (egg only) 自作の汎用 matplotlib/wx package です．
-->


## Contributing

Please read [CONTRIBUTING](./CONTRIBUTING) for details on our code of conduct, and the process for submitting pull requests to us.

See also readme files included in each package for detail.


## Authors

* Kazuya O'moto - *Initial work* -

See also the list of who participated in this project.


## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details
