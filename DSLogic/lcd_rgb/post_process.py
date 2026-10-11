#! python3
''' 对LCD RGB解码后并“协议导出”的数据后处理
	导出的文件必须为两个，且分别命名为imageL.csv和imageH.csv，
	此脚本从两个文件中分别提取一个完整帧的数据并将两组8位数据合并
	成一组16位数据，保存到image.bin文件中，同时将数据按照RGB565格式转换成图片显示
'''

def get_one_frame(file_name):
	arrS = [line[line.rindex(',')+1:].strip() for line in open(file_name, 'r')]
	arrS = arrS[arrS.index('vsync')+1:]
	arrS = arrS[:arrS.index('vsync')]
	arrS = [x for x in arrS if x != 'hsync']
	arrN = [int(x, 16) for x in arrS]

	return arrN

arrL = get_one_frame('imageL.csv')
arrH = get_one_frame('imageH.csv')
arr  = [(h<<8)+l for (l, h) in zip(arrL, arrH)]

open('image.bin', 'wb').write(b''.join(x.to_bytes(2, byteorder='little') for x in arr))


from pylab import *

img = [(((x>>11)&0x1F)<<3, ((x>>5)&0x3F)<<2, (x&0x1F)<<3) for x in arr]
img = array(img, dtype=np.uint8).reshape(272, 480, 3)
imshow(img)
show()
