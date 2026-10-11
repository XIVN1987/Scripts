#! python3
import os
import sys
import struct
import argparse

parser = argparse.ArgumentParser(description=u"generate Quartus Memory Initialization File from *.bin")
parser.add_argument('-i', dest='input',  help='input  *.bin file')
parser.add_argument('-o', dest='output', help='output *.mif file')
parser.add_argument('-w', dest='width',  help='bits per word')
parser.add_argument('-d', dest='depth',  help='word count in output file')
parser.add_argument('-f', dest='fill',   help='data used to fill output file')

args = parser.parse_args()

if not args.input or not os.path.isfile(args.input):
    print('must give input file')
    sys.exit(-1)

try:
    width = int(args.width)
    if width not in (8, 16, 32):
        raise Exception()
except Exception as e:
    print("argument 'width' not valid")
    sys.exit(-1)

try:
    if args.depth.startswith('0'):
        depth = int(args.depth, 16)
    else:
        depth = int(args.depth)
except Exception as e:
    print("argment 'depth' not valid")
    sys.exit(-1)

try:
    if args.fill.startswith('0'):
        fillv = int(args.fill, 16)
    else:
        fillv = int(args.fill)
except Exception as e:
    fillv = int('1' * width, 2)


with open(args.output, 'w') as fw:
    fw.write('WIDTH = %d;\n' %width)
    fw.write('DEPTH = %d;\n' %depth)
    fw.write('ADDRESS_RADIX = HEX;\n')
    fw.write('DATA_RADIX    = HEX;\n')

    fw.write('CONTENT\nBEGIN\n')

    bytes = open(args.input, 'rb').read()
    if width == 8:
        fmt = 'B'
        cnt = len(bytes)
    elif width == 16:
        if len(bytes) % 2: bytes += b'\xFF'
        fmt = 'H'
        cnt = len(bytes) / 2
    elif width == 32:
        if len(bytes) % 4: bytes += b'\xFF' * (4 - len(bytes))
        fmt = 'L'
        cnt = len(bytes) / 4
    
    integers = struct.unpack('<%d%s' %(cnt, fmt), bytes)
    integers += (fillv,) * (depth - len(integers))

    fw.write('\n'.join('%X: %08X;' %(i, x) for (i, x) in enumerate(integers)))

    fw.write('\nEND;\n');
