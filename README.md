# wxpj

A package for Image analysis and TEM control


## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

私の環境では以下のバージョンで動作しています．
    
    <Python 3.5.4 (v3.5.4:3f56838, Aug  8 2017, 02:17:05) [MSC v.1900 64 bit (AMD64)]>
        wx.version(selected) 4.0.7.post2 msw (phoenix) wxWidgets 3.0.5
        scipy/numpy version 1.2.1/1.18.1
        matplotlib verison 3.0.3
        Image verison 7.0.0
        cv2 verison 3.4.5
        mwx 0.20

### Prerequisites

0. Install PY35

    Currently required environs: PY35.
        
        !! PYJEM 機能を使用するためには PY <= 3.5 (以下) をインストールしてください．
        !! 別途，TemExternal のインストールが必要です．
    
    標準 CPython をインストールしてください．
    
        Anaconda の古いやつだと wxPython のインストールがコケます．
        Anaconda バージョン管理でコケることがあるので推奨しません．

### Installing

1. Install packages

    To setup environment necessary to work, do pip install.
    ```
    $ python -m pip install -U pip setuptools
    $ pip install scipy==1.2.3 pillow matplotlib opencv-python==3.4.5.20 wxpython==4.0.7 pywin32
    $ pip install PyJEM-1.0.2.1143.zip httplib2
    ```

<!--
2. Get wxpj from db

pyJemacs_noarch_cp35_#date.7z を解凍して適当な場所に置く．7z が別途必要です．
-->

2. Clone wxpj from Git site
    ```
    $ git clone http://dl-box.jeol.co.jp/gitbucket/git/komoto/wxpj.git
    ```


## How to execute wxpyJemacs

### スクリプト実行の場合
```
$ py -3.5 wxpyjemacs.py --pyjem=None -suser
```
    --pyjem: pyjem 拡張の使用を宣言します
        Launch wxpyJemacs with --pyjem=0(=offline), 1(=online), or 2(=online with TEM3)
        The defalut switch is --pyjem=None, that means no PyJEMs to be involved.
        
        ▲ TEM3.online を宣言しない場合，
        アプリケーション起動後に TEM3 を含むプラグインを組み込むことは一切できません
        
        ▲ TEM3.online を宣言した場合，
        DnD, CnP などの Windows shell ex はすべて使用不可になります．
    
    -sxxx: xxx セッションで開始します
        セッションとは，プロジェクトファイル的なやつで，
        プラグイン拡張，ウィンドウレイアウト，バッファとかをおーざっぱに保持します


### バイナリ実行の場合

*** 現在バイナリ版はリリースしていません***
```
$ pJ.cmd
```
    バイナリパッケージは実行に必要なランタイムをすべて含んでいますが，
    Windows 10 64bit (AMD64) 以外の OS では実行できません．
    (たぶん OpenCV の dll バージョンが合わないため)


## Deployment

Additional notes about how to deploy this on a live system

    !! PYJEM.TEM3 機能を使用するためには PY <= 3.5 (以下) をインストールしてください．
    !! 別途，TemExternal のインストールが必要です．


## Built With

* [pyDM3reader] - Python DM3 Reader (originated from ImageJ plugin)

* [pyGatan] - Leginon のサイトにある Python 2.7 用スクリプトを Python 3 で動くように修正したもの

* [pyJeol.egg] (未公開) JEOL legacy TEM package です．主に次のモジュールで構成されます．
    - pyJem: PyJEM wrapper
    - pyJem2: Poor man's PyJEM
    - plugman: JEOL TEM Notify manager

* [mwxlib.egg] (未公開) 自作の汎用 wxpython package です．


## Contributing

Please read [CONTRIBUTING](./CONTRIBUTING) for details on our code of conduct, and the process for submitting pull requests to us.

See also readme files included in each package for detail.


## Authors

* Kazuya O'moto - *Initial work* -

See also the list of who participated in this project.


## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details
