#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import argparse
import os.path

# TODO: Handle Extended APP0 Marker
# TODO: Ensure the JPEG ends with FF D9
# TODO: Handle Thumbnail


def read_chunk(f, chunk_size):
    while True:
        data = f.read(chunk_size)
        if not data:
            break
        yield data


def write_file(jpgh, pdfh, fh):
    bs = b""
    bs += jpgh.read(0x14)  # JFIF APP0 Marker Segment without thumbnail
    try:
        assert(bs[0x0:0x2] == b"\xFF\xD8")
        assert(bs[0x2:0x4] == b"\xFF\xE0")
        assert(bs[0x6:0xB] == b"\x4A\x46\x49\x46\x00")
    except:
        print("%s" % bs[0x0:0xA])
        raise

    thumbnail_width = int(bs[0x12])
    thumbnail_height = int(bs[0x13])

    thumbnail_size = 3 * thumbnail_width * thumbnail_height

    thumbnail_data = b""
    if thumbnail_size > 0:
        thumbnail_data = jpgh.read(thumbnail_size)  # Discard thumbnail

    fh.write(bs[0x0:0x2])  # 2 - Start of image
    fh.write(b"\x00\x00")  # 2 - APP0 Marker, Bypass Adobe filter
    fh.write(bs[0x4:0x6])  # 2 - Length of segment
    fh.write(bs[0x6:0xB])  # 5 - JFIF Magic Marker
    fh.write(bs[0xB:0xD])  # 2 - JFIF Version
    fh.write(bs[0xD:0xE])  # 1 - Density units
    fh.write(bs[0xE:0x10])  # 2 - Horizontal density
    fh.write(bs[0x10:0x12])  # 2 - Vertical density
    fh.write(b"\x00")  # 1 - Horizontal thumbnail pixel count
    fh.write(b"\x00")  # 1 - Vertical thumbnail pixel count

    fh.write(b"\xFF\xFE")  # 2 - Comment JFIF Marker
    fh.write(b"\x00\x22")  # 2 - Size of the payload

    # Write PDF Payload (dummy object)
    ps = b""
    ps += pdfh.read(0x200)
    i = ps.find(b"\x0A")
    fh.write(b"\x0A")
    fh.write(ps[0x0:i])
    fh.write(
        (b"\x0A\x39\x39\x39\x20\x30\x20\x6F\x62\x6A\x0A\x3C\x3C\x3E\x3E"
         b"\x0A\x73\x74\x72\x65\x61\x6D\x0A")
    )

    # Write picture data
    for bs in read_chunk(jpgh, 0x200):
        fh.write(bs)

    # Ending dummy object
    fh.write(
        (b"\x0A\x65\x6E\x64\x73\x74\x72\x65\x61\x6D\x0A\x65\x6E\x64\x6F\x62"
         b"\x6A\x0A")
    )
    fh.write(ps)
    for ps in read_chunk(pdfh, 0x200):
        fh.write(ps)


def main(args):
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument(
        '--pdf',
        required=True,
        help='The path of the pdf file'
    )
    parser.add_argument(
        '--jpg',
        required=True,
        help='The path of the jpeg file'
    )
    parser.add_argument(
        '-o',
        required=True,
        metavar='OUTPUT',
        help='The path of the output file'
    )

    args = parser.parse_args()

    args.jpg = os.path.realpath(args.jpg)
    args.pdf = os.path.realpath(args.pdf)

    print(args)

    with open(args.jpg, 'rb') as jpgh, open(args.pdf, 'rb') as pdfh:
        with open(args.o, 'wb') as fh:
            write_file(jpgh, pdfh, fh)

if __name__ == '__main__':
    main(sys.argv)
