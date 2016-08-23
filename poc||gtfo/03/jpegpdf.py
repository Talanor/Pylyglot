#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import argparse
import os.path

# TODO: Handle Thumbnail


def read_chunk(f, chunk_size):
    while True:
        data = f.read(chunk_size)
        if not data:
            break
        yield data


def write_file(jpgh, pdfh, fh):
    bs = jpgh.read(0x14)  # JFIF APP0 Marker Segment without thumbnail
    try:
        assert(bs[0x0:0x2] == b"\xFF\xD8")
        assert(bs[0x2:0x4] == b"\xFF\xE0")
        assert(bs[0x6:0xB] == b"JFIF\x00")
    except:
        print("%s" % bs[0x0:0xB])
        raise
    else:
        print("Probably well formatted JFIF")

    print("Analyzing APP0 Marker Segment")
    thumbnail_width = int(bs[0x12])
    thumbnail_height = int(bs[0x13])

    print("Thumbnail dimensions: (%dx%d)" % (
        thumbnail_width, thumbnail_height
    ))

    thumbnail_size = 3 * thumbnail_width * thumbnail_height

    thumbnail_data = b""
    if thumbnail_size > 0:
        thumbnail_data = jpgh.read(thumbnail_size)  # Read thumbnail
        print("Discarding the thumbnail")

    print("Writing Patched APP0 Marker segment to PDF file")
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

    print("%s" % (
        bs[0x0:0x2] + b"\x00\x00" + bs[0x4:0x6] + bs[0x6:0xB] + bs[0xB:0xD] +
        bs[0xD:0xE] + bs[0xE:0x10] + bs[0x10:0x12] + b"\x00" + b"\x00"
    ))

    bs += jpgh.read(0x200)

    print("Checking JFIF Version")
    print("%d.%d" % (bs[0xB], bs[0xC]))

    # Check that JFIF version >= 1.02
    # The goal of these lines is to get the JPEG data after the
    # extended APP0 header
    if int(bs[0xB]) > 1 or (int(bs[0xB]) == 1 and int(bs[0xC]) >= 2):
        print("JFIF version >= 1.02")
        # Check that Extented APP0 Marker segment is present
        if bs[0x14:0x16] == b"\xFF\xE0" and bs[0x18:0x1D] == b"JFXX\x00":
            print("APP0 Extended Marker Segment found")
            offset = 0
            fh.write(bs[0x14:0x1D])  # Write beginning of Extended Marker
            bs = bs[0x1D:]
            buff = bs  # Keep only the whole thumbnail for rewriting sake

            # Thumbnail stored using JPEG Encoding
            if int(bs[0x0]) == 0x10:
                print("Thumbnail stored using JPEG Encoding")
                # Asserts the start of the thumbnail
                assert(bs[0x1:0x3] == b"\xFF\xD8")

                while True:
                    i = bs.find(b"\xFF\xD9")  # Search end of thumbnail
                    if i > -1:
                        offset += i + 2
                        bs = bs[i + 2:]
                        break
                    else:
                        offset += len(bs)
                        bs = jpgh.read(0x200)
                        buff += bs
                        if not bs:
                            raise ValueError("Could not find end of thumbnail")
            # Thumbnail stored using one byte per pixel
            elif int(bs[0x0]) == 0x11:
                print("Thumbnail stored using one byte per pixel")
                assert(int(bs[0x1]) > 0 and int(bs[0x2]) > 0)

                # Read the thumbnail header data

                to_read = (0x302 + int(bs[0x1]) * int(bs[0x2])) - \
                    (len(bs) - 0x1 - 0x2)

                if to_read > 0:
                    buff += jpgh.read(to_read)
                    offset = len(buff)
                    bs = b""
                else:
                    offset = to_read
                    bs = bs[len(bs) + to_read:]
            # Thumbnail stored using three bytes per pixel
            elif int(bs[0x0]) == 0x13:
                print("Thumbnail stored using three bytes per pixel")
                assert(int(bs[0x1]) > 0 and int(bs[0x2]) > 0)

                # Read the thumbnail header data

                to_read = (3 * int(bs[0x1]) * int(bs[0x2])) - \
                    (len(bs) - 0x1 - 0x2)

                if to_read > 0:
                    buff += jpgh.read(to_read)
                    offset = len(buff)
                    bs = b""
                else:
                    offset = to_read
                    bs = bs[len(bs) + to_read:]
            else:
                raise ValueError("Unexpected thumbnail format")
            # Write the whole thumbnail along with its format
            fh.write(buff[:offset])
    else:
        print("No APP0 Extended Marker Segment possibly found")
        bs = bs[0x14:]

    print("Writing JFIF Comment Marker")
    fh.write(b"\xFF\xFE")  # 2 - Comment JFIF Marker

    payload = (
        (b"\x39\x39\x39\x20\x30\x20\x6F\x62\x6A\x0A\x3C\x3C\x3E\x3E"
         b"\x0A\x73\x74\x72\x65\x61\x6D\x0A"),
        (b"\x0A\x65\x6E\x64\x73\x74\x72\x65\x61\x6D\x0A\x65\x6E\x64\x6F\x62"
         b"\x6A\x0A")
    )

    print("Writing PDF's Dummy Object Payload")
    # Write PDF Payload (dummy object)
    ps = pdfh.read(0x200)
    try:
        assert(ps[0x0:0x4] == b"%PDF")
    except:
        print("%s" % ps[0x0:0x4])
        raise

    pdf_mark = b"\x0A%PDF-1.5\x0A"

    fh.write(
        (len(pdf_mark) + len(payload[0]) + 0x2).to_bytes(
            2, byteorder='big'
        )
    )  # 2 - Size of the payload

    fh.write(pdf_mark)
    fh.write(payload[0])

    print("Writing picture data")
    # Write picture data
    last = b""
    fh.write(bs)
    for bs in read_chunk(jpgh, 0x200):
        fh.write(bs)
        last = last + bs
        last = last[-2:]

    assert(last == b"\xFF\xD9")

    print("Writing the end of PDF Dummy Object")
    # Ending dummy object
    fh.write(payload[1])
    print("Writing PDF content")
    fh.write(ps)
    for ps in read_chunk(pdfh, 0x200):
        fh.write(ps)


def main(args):
    parser = argparse.ArgumentParser(
        description='Make a polyglot file out of a JPEF and a PDF.'
    )
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

    with open(args.jpg, 'rb') as jpgh, open(args.pdf, 'rb') as pdfh:
        with open(args.o, 'wb') as fh:
            write_file(jpgh, pdfh, fh)

if __name__ == '__main__':
    main(sys.argv)
