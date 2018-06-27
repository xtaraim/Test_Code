# -*- mode: python -*-

import os

block_cipher = None

data_files = [
                ('darknet/darknet', 'darknet'),
                ('darknet/libdarknet.so', 'darknet'),
                ('darknet/cfg/coco.data', 'darknet/cfg'),
                ('darknet/cfg/yolov3.cfg', 'darknet/cfg'),
                ('darknet/data/coco.names', 'darknet/data'),
                ('darknet/weights/yolov3.weights', 'darknet/weights')
             ]

a = Analysis(['http_handler.py'],
             pathex=[os.getcwd()],
             binaries=[],
             datas=data_files,
             hiddenimports=['pandas._libs.tslibs.timedeltas'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='GoDeep',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True)
