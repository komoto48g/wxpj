# wxpj

A package for Image analysis and TEM control


## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

私の環境では 2023/6/20 現在，以下のバージョンで動作しています．
```Python 3.10.11
  <Python 3.10.11 (tags/v3.10.11:7d4cc5a, Apr  5 2023, 00:38:17) [MSC v.1929 64 bit (AMD64)]>
  wx version 4.2.1 msw (phoenix) wxWidgets 3.2.2.1
  scipy/numpy version 1.10.1/1.24.2
  matplotlib version 3.7.1/WXAgg
  Image version 9.5.0
  cv2 version 4.7.0
  mwx 0.85.6
```

![setup](./images/net.png)


### Prerequisites

:memo: wxpj 0.46 `GOOD BYE PYJEM` becomes PyJEM-independent.

***Don't use Anaconda because wxPython cannot be installed.***

* ~~[Python 3.8.6 for Windows](https://www.python.org/downloads/release/python-386/)  
    if you use PyJEM, this version is recommended.~~

* [Python 3.10.11 for Windows](https://www.python.org/downloads/release/python-31011/)  
    This version is for `GOOD BYE PYJEM`.

* [Git for Windows](https://git-scm.com/)  
    required to pip-install the latest modules from GitHub.


### Installing

Create a workspace or venv to install.

1. Install Python packages (from pypi) using batch files  

    To install PY310+ packages:
    ```
    pip install -U pywin32 httplib2 mwxlib
    git clone https://github.com/komoto48g/wxpj.git
    ```


#### Note (for internal use only)

社内からインストールする場合プロキシが見つからない為に失敗するかもしれません．
その場合はまず次の設定を行ってください


    set HTTPS_PROXY=http://i-net.jeol.co.jp:80
    set HTTP_PROXY=http://i-net.jeol.co.jp:80


### Updating

To update packages, follow the steps above again.
<!--
Remove the wxpj directory before updating. Otherwise the latest wxpj will not be cloned.
-->
To update wxpj:

    $ cd wxpj
    $ git pull


## How to execute wxpyJemacs

Here, let "~/" be the directory the main program is cloned.

Launch the program:

    $ python ~/wxpyJemacs.py


## How to terminate wxpyJemacs

Press [x] Button.

When you close the program, a popup window will appear asking "Do you want to save session before closing program?".
The session is like a project file, and it roughly saves plugins, parameters, windows layouts, buffers, etc.
Click [OK]. Then, the next time you start the program with the session file, you can start it in the same state as when it was last closed.


## How to restart the session

To restart the session, launch the program with -s switch:

    $ python ~/wxpyJemacs.py -s<session file.jssn>

Then, the program will start in the same state as when the session was saved.


## Deployment

Additional notes about how to deploy this on a live system

    !! PYJEM.TEM3 機能を使用するためには PY <= 3.5 (以下) をインストールしてください．
    !! 別途，TemExternal のインストールが必要です．

<!--
:memo: バージョン 0.46 以降では不要になります．↑
       No longer required after version 0.46.
-->


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


## Contributing

Please read [CONTRIBUTING](./CONTRIBUTING) for details on our code of conduct, and the process for submitting pull requests to us.

See also readme files included in each package for detail.


## Authors

* Kazuya O'moto - *Initial work* -

See also the list of who participated in this project.


## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details
