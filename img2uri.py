#! python3
import os
import binascii

srcdir = r'C:\Users\WMX\Desktop'

for name in os.listdir(srcdir):
    fext = os.path.splitext(name)[1]
    if fext in ['.png', '.jpg', '.gif']:
        path = os.path.join(srcdir, name)
        img_bin = open(path, 'rb').read()
        img_uri = f'<img src="data:image/{fext[1:]};base64,{binascii.b2a_base64(img_bin, newline=False).decode("latin-1")}">'
        open(path+'.uri', 'w', encoding='utf-8').write(img_uri)
