# wxpj

A package for Image analysis and TEM control


## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

私の環境では以下のバージョンで動作しています．
```
<Python 3.8.6 (tags/v3.8.6:db45529, Sep 23 2020, 15:52:53) [MSC v.1927 64 bit (AMD64)]>
  wx.version(selected) 4.1.1 msw (phoenix) wxWidgets 3.1.5
  scipy/numpy version 1.6.0/1.20.1
  matplotlib verison 3.4.2
  Image verison 8.1.0
  cv2 verison 4.5.1
  mwx 0.40
```

### Prerequisites

![setup](man/image/net.png)

### Installing

Create a workspace and install it in it. 
Please prepare `PyJEM-*.zip` in advance.
Please Install [Python 3.5.4 for Windows](https://www.python.org/downloads/release/python-354/).
***Don't use Anaconda because wxPython cannot be installed.***
Please also install [Git for Windows](https://git-scm.com/) in advance,
which is required to pip-install the latest modules from GitHub.

1. Prepare the workspace directory as follows.
```
<your-workdir>
    ├ make-py35.bat (batch file for installation)
    ├ PyJEM-1.0.2.1143.zip (PyJEM package)
    ├ pJ.cmd (batch file for startup)
    └ siteinit.py (initial setting)
```
2. Install Python packages (from pypi) using [make-py35.bat](man/make-PY35.bat) file.
    ```
    $ make-py35.bat
    ```

3. To update packages, use [make-py35-update.bat](man/make-PY35-update.bat) file.
    ```
    $ make-py35-update.bat
    ```

#### Installing Note (For internal use only)

- 社内からインストールする場合プロキシが見つからない為に失敗するかもしれません．
  その場合はまず次の設定を行ってください
```
$ set HTTPS_PROXY=http://i-net.jeol.co.jp:80
$ set HTTP_PROXY=http://i-net.jeol.co.jp:80
```

<!--
1. 適当なディレクトリ (Your-workdir) を作成し，社内専用レポジトリから .zip をダウンロードして展開します．
     - [wxpj-master](http://dl-box.jeol.co.jp/gitbucket/komoto/wxpj)
     - [wxpj-aero-master](http://dl-box.jeol.co.jp/gitbucket/komoto/wxpj-aero) 

2. PyJEM は社内 ノーツデータベースから *PyJEM-1.0.2.1143.zip* をダウンロードしてください (zip の展開は不要)
ディレクトリ構成は以下のようになります．
```
<your-workdir>
    ├ <wxpj-master>
    ├ <wxpj-aero-master>
    ├ PyJEM-1.0.2.1143.zip (PyJEM package)
    ├ pJ.cmd (batch file for startup)
    └ siteinit.py (initial setting)
```

4. Install packages
    - To setup wxpj, do pip install.
      コマンドプロンプトを起動して以下のコマンドを順番に実行します ($ はプロンプトなので無視)
    ```
    $ py -3.5 -m pip install -U pip
    $ py -3.5 -m pip install -r wxpj-mater/requirements.txt
    $ py -3.5 -m pip install PyJEM-1.0.2.1143.zip
    ```
-->

## How to execute wxpyJemacs

Launch `wxpj/wxpyJemacs.py`.

When you close the program, a popup window will appear asking [Do you want to save session before closing program?].

> The session is like a project file, and it roughly saves plugins, paramteres, windows layouts, buffers, etc.

Click [OK]. Then, the next time you start the program with the session file, you can start it in the same state as when it was last closed. The extension of the session file is `*.jssn`. 


## How to start session

Start from the command prompt using [pJ.cmd](man/pJ.cmd):
```
$ pj user
```
which is equivalent to the following:
```
$ py -3.5 wxpj/wxpyjemacs.py --pyjem=1 -suser
```
The meanings of the command arguments are:

    --pyjem: Declare using pyjem

        Launch wxpyJemacs with --pyjem=0(=offline), 1(=online), or 2(=online with TEM3)
        The defalut switch is --pyjem=None, that means no PyJEMs to be involved.
        Please use flag `1` normaly.

    -sxxx: Start xxx session


## Deployment

Additional notes about how to deploy this on a live system

    !! PYJEM.TEM3 機能を使用するためには PY <= 3.5 (以下) をインストールしてください．
    !! 別途，TemExternal のインストールが必要です．


## Built With

* [pyDM4reader] - Python DM4 Reader (https://github.com/jamesra/dm4reader)

* [pyDM3reader] - Python DM3 Reader (https://github.com/komoto48g/pyDM3reader)
    元々は ImageJ plugin で Greg Jefferis 氏によって python 化されたやつの porting PY2 to 3 by komoto

* [pyGatan] - Leginon のサイトにある Python 2.7 用スクリプトを Python 3 で動くように修正したもの
    by hiijima

* [pyJeol] (egg only) JEOL legacy TEM package です．主に次のモジュールで構成されます．
    - pyJem: Facade of PyJEM
    - pyJem2: Poor man's PyJEM
    - plugman: JEOL TEM Notify manager

* [mwxlib] (egg only) 自作の汎用 matplotlib/wx package です．
    おーざっぱにいうと以下のモジュールで構成されます．
    - controls: wx custom controls
    - framework: the framework
    - graphman: graph manager
    - matplot2/g/lg: wrapper of matplotlib


## Contributing

Please read [CONTRIBUTING](./CONTRIBUTING) for details on our code of conduct, and the process for submitting pull requests to us.

See also readme files included in each package for detail.


## Authors

* Kazuya O'moto - *Initial work* -

See also the list of who participated in this project.


## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details
