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

![setup](image/net.png)
<!--
<img src=image/net.png width=600>
-->

0. Install PY35

    Currently required environs: PY35
    (標準 CPython をインストールしてください)
    
    - PYJEM 機能を使用するために PY <= 3.5 (以下) をインストールしてください．
    - 別途，TemExternal のインストールが必要です．
    - Anaconda の古いやつだと wxPython のインストールがコケます．
    - Anaconda はバージョン管理でよくずっコケるので推奨しません．

### Installing

1. Install packages

    - To setup environment necessary to work, do pip install.
      (コマンドプロンプトを起動して以下のコマンドを順番に実行します)
    ```
    $ py -3.5 -m pip install -U pip
    $ py -3.5 -m pip install scipy==1.2.3 opencv-python==3.4.5.20 pillow matplotlib wxpython==4.0.7
    $ py -3.5 -m pip install pywin32 openpyxl flake8 httplib2
    ```
    - 社内からインストールする場合プロキシが見つからない為に失敗するかもしれません．
      その場合はまず次の設定を行ってください
    ```
    $ set HTTPS_PROXY=http://i-net.jeol.co.jp:80
    $ set HTTP_PROXY=http://i-net.jeol.co.jp:80
    ```
    - You can also use this.
      (これも使えます)
    ```
    $ py -3.5 -m pip install -U pip
    $ py -3.5 -m pip install -r requirements.txt
    ```

2. Download wxpj from Git site
    社内レポジトリサーバーからダウンロードして，適当なところに展開してください
    [wxpj@GitBucket](http://dl-box.jeol.co.jp/gitbucket/komoto/wxpj)

3. Download PyJEM from DB
    社内 ノーツデータベースから *PyJEM-1.0.2.1143.zip* をダウンロードして，同じディレクトリにコピーしてください（展開は不要）
    [NotesLink](Notes://NotesOffice/4925805700077587/DD11EF58D84D230E4925646F003E2CF8/162DB45516A951F4492580570007AA5D)
    *Automation & PyJEM - PyJEM & AutomationCenter導入*
    ```
    $ py -3.5 -m pip install PyJEM-1.0.2.1143.zip
    ```

準備は以上です


## How to execute wxpyJemacs

### スクリプト実行の場合
```
$ py -3.5 wxpyjemacs.py --pyjem=None -suser
```
    --pyjem: pyjem 拡張の使用を宣言します
    
        Launch wxpyJemacs with --pyjem=0(=offline), 1(=online), or 2(=online with TEM3)
        The defalut switch is --pyjem=None, that means no PyJEMs to be involved.
<!--
▲ TEM3:online を宣言しない場合，
アプリケーション起動後に TEM3 を含むプラグインを組み込むことは一切できません
▲ TEM3:online を宣言した場合，
DnD, CnP などの Windows shell ex はすべて使用不可になりますので注意してください．
-->
    -sxxx: xxx セッションで開始します
    
        セッションとは，プロジェクトファイル的なやつで，
        プラグイン拡張，ウィンドウレイアウト，バッファとかをおーざっぱに保持します

<!--
### バイナリ実行の場合
バイナリパッケージは実行に必要なランタイムをすべて含んでいますが，
Windows 10 64bit (AMD64) 以外の OS では実行できません．
(たぶん OpenCV の dll バージョンが合わないため)
-->


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

* [mwxlib] (egg only) 自作の汎用 matplotlib/wx package です．以下のモジュールで構成されます．
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
