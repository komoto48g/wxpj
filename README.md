wxpj
===============

A package for TEM control

���̊��ł͈ȉ��̃o�[�W�����œ��삵�Ă��܂��D

    <Python 3.5.4 (v3.5.4:3f56838, Aug  8 2017, 02:17:05) [MSC v.1900 64 bit (AMD64)]>
        wx.version(selected) 4.0.7.post2 msw (phoenix) wxWidgets 3.0.5
        scipy/numpy version 1.2.1/1.18.1
        matplotlib verison 3.0.3
        Image verison 7.0.0
        cv2 verison 3.4.5
        mwx 0.20


How to install
--------------

pyJemacs_noarch_cp35_#date.7z ���𓀂��ēK���ȏꏊ�ɒu���D
7z ���ʓr�K�v�ł��D

**To setup environment necessary to work, do pip install,**

Currently required environs: PY35

$ python -m pip install -U pip setuptools  
$ pip install scipy==1.2.3 pillow matplotlib opencv-python==3.4.5.20 wxpython==4.0.7 pywin32  
$ pip install PyJEM-1.0.2.1143.zip httplib2  

    !! PYJEM �@�\���g�p���邽�߂ɂ� PY <= 3.5 (�ȉ�) ���C���X�g�[�����Ă��������D
    !! �ʓr�CTemExternal �̃C���X�g�[�����K�v�ł��D


How to execute wxpyJemacs
-------------------------

### 1a �o�C�i�����s�̏ꍇ
$ pJ.cmd

    �o�C�i���p�b�P�[�W�͎��s�ɕK�v�ȃ����^�C�������ׂĊ܂�ł��܂����C
    Windows 10 64bit (AMD64) �Ńr���h����Ă��邽�߁C���̑��� OS �ł͎��s�ł��܂���D
    (���Ԃ� OpenCV �� dll �o�[�W����������Ȃ�����)


### 1b �X�N���v�g���s�̏ꍇ
$ python wxpyjemacs.py -suser --pyjem=None

    -sxxx: xxx �Z�b�V�����ŊJ�n���܂�
        �Z�b�V�����Ƃ́C�v���W�F�N�g�t�@�C���I�Ȃ�ŁC
        �v���O�C���g���C�E�B���h�E���C�A�E�g�C�o�b�t�@�Ƃ������[�����ςɕێ����܂�

    --pyjem: pyjem �g���̎g�p��錾���܂�
        Launch wxpyJemacs with --pyjem=0(=offline), 1(=online), or 2(=online with TEM3)
        The defalut switch is --pyjem=None, that means no PyJEMs to be involved.
        ���A�v���P�[�V�����N����� PYJEM ���܂ރv���O�C����g�ݍ��ނ��Ƃ͈�؂ł��܂���
