wxpj
===============

A package for Image analysis and TEM control

私の環境では以下のバージョンで動作しています．

    <Python 3.5.4 (v3.5.4:3f56838, Aug  8 2017, 02:17:05) [MSC v.1900 64 bit (AMD64)]>
        wx.version(selected) 4.0.7.post2 msw (phoenix) wxWidgets 3.0.5
        scipy/numpy version 1.2.1/1.18.1
        matplotlib verison 3.0.3
        Image verison 7.0.0
        cv2 verison 3.4.5
        mwx 0.20


How to install
--------------

0. Install PY35 
標準 CPython をインストールしてください．

    Anaconda の古いやつだと wxPython のインストールがコケるみたいです．
    Anaconda バージョン管理でコケることがあるので推奨しません．

1. Install python packages 

**To setup environment necessary to work, do pip install,**

Currently required environs: PY35
```
$ python -m pip install -U pip setuptools  
$ pip install scipy==1.2.3 pillow matplotlib opencv-python==3.4.5.20 wxpython==4.0.7 pywin32  
$ pip install PyJEM-1.0.2.1143.zip httplib2  
```

    !! PYJEM 機能を使用するためには PY <= 3.5 (以下) をインストールしてください．
    !! 別途，TemExternal のインストールが必要です．

<!--
2. Get wxpj from db

pyJemacs_noarch_cp35_#date.7z を解凍して適当な場所に置く．7z が別途必要です．
-->

2. Clone wxpj from Git site
```
$ git clone http://dl-box.jeol.co.jp/gitbucket/git/komoto/wxpj.git
```


How to execute wxpyJemacs
-------------------------

<!--
### バイナリ実行の場合
$ pJ.cmd

    バイナリパッケージは実行に必要なランタイムをすべて含んでいますが，
    Windows 10 64bit (AMD64) でビルドされているため，その他の OS では実行できません．
    (たぶん OpenCV の dll バージョンが合わないため)
-->

### スクリプト実行の場合
$ python wxpyjemacs.py -suser --pyjem=None

    -sxxx: xxx セッションで開始します
        セッションとは，プロジェクトファイル的なやつで，
        プラグイン拡張，ウィンドウレイアウト，バッファとかをおーざっぱに保持します

    --pyjem: pyjem 拡張の使用を宣言します
        Launch wxpyJemacs with --pyjem=0(=offline), 1(=online), or 2(=online with TEM3)
        The defalut switch is --pyjem=None, that means no PyJEMs to be involved.
        ▲アプリケーション起動後に PYJEM を含むプラグインを組み込むことは一切できません


使用条件など
------------

[LICENSE](./LICENSE) を参照してください。
