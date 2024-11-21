# wxpj

A package for Image analysis and TEM control


## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.


### Prerequisites

![setup](./images/network.png)


#### Note (for internal use only)

社内でインストールする場合プロキシが見つからない為に失敗するかもしれません．
その場合はまず次の設定を行ってください

    $ set HTTPS_PROXY=http://i-net.jeol.co.jp:80
    $ set HTTP_PROXY=http://i-net.jeol.co.jp:80


### Installing

1. Install Python.
    - Supports Python 3.10, 3.11, and 3.12.
    - Supports Python 3.13, but a few minor bugs are still unresolved.
    - ***Please avoid using Anaconda, as wxPython cannot be installed.***

2. Install Python packages:
    ```
    $ pip install -U pywin32 httplib2 mwxlib
    ```

3. Install wxpj software.
    To download and install the wxpj project, follow these steps:
    1. Access the repository:
        Go to the [wxpj GitHub repository](https://github.com/komoto48g/wxpj).
    2. Download as ZIP:
        - On the repo's main page, click the green "Code" button.
        - In the dropdown menu, select "Download ZIP".
    3. Extract the ZIP file:
        - After downloading, locate the ZIP file on your computer.
        - Decide a destination folder and extract the contents.


## How to run wxpyJemacs

Here, let "~/" represent the directory where the main program is unzipped.
The main program file is "wxpyjemacs.py".

Launch the program:

    $ python ~/wxpyJemacs.py


## How to terminate wxpyJemacs

Press [x] Button.

When you close the program, a popup window will appear asking "Do you want to save session before closing program?".
The session is like a project file, saving infomation such as plugins, parameters, windows layouts, buffers, and more.
Click [OK] to save. Then the next time you start the program with the session file, it will restore the program to the same state as when it was last closed.


## How to restart the session

To restart the session, launch the program with `-s` switch:

    $ python ~/wxpyJemacs.py -s<session file.jssn>

Then, the program will start in the same state as when the session was saved.


### Tips

以下のようなバッチファイルを，メインプログラムのディレクトリと同じ場所に置き，`.jssn` を関連付けます．
これにより，`.jssn` をダブルクリックすることでプログラムが起動し，セッションを再開することができます．

pJ.cmd
```
python "%~dp0\wxpj-master\wxpyJemacs.py" -s%1
```

> 関連付けの方法 (Windows 11 の場合)
> 1. `.jssn` ファイルを右クリックする
> 2. 「プログラムから開く」→「別のプログラムを選択」
> 3. 「PC でアプリを選択する」→ "pJ.cmd" を選択する．
> 4. 「常に使う」を押して実行する．


## Deployment

Additional notes about how to deploy this on a live system

    !! PYJEM.TEM3 機能を使用するためには PY <= 3.5 (以下) をインストールしてください．
    !! 別途，TemExternal のインストールが必要です．

<!--
:memo: バージョン 0.46 以降では不要です．
       No longer required after version 0.46 GOOD BYE PYJEM.
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
