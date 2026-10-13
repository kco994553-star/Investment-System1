"""Price-free, local-only company logo images bundled during an Actions build."""
from __future__ import annotations
import base64
import json
import struct
import zlib
from investment_system.universe.universe_domains import all_codes

FILENAME = 'company-logos.json'
SCHEMA = 'company-logos/1'
PREFIX = 'data:image/png;base64,'
MAX_IMAGE_BYTES = 32 * 1024
MAX_BUNDLE_BYTES = 1536 * 1024


def _chunk(kind: bytes, value: bytes) -> bytes:
    return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value) & 0xffffffff)


def sanitize_png(content: bytes) -> bytes:
    """Decode bounded PNG pixels and write metadata-free, noninterlaced RGBA8."""
    error = 'LOGO_PNG_INVALID'
    if not isinstance(content, bytes) or len(content) > MAX_IMAGE_BYTES or not content.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError(error)
    index, image_data, header, ended, data_closed = 8, b'', None, False, False
    palette, transparency = None, None
    legal = {0: (1,2,4,8,16), 2: (8,16), 3: (1,2,4,8), 4: (8,16), 6: (8,16)}
    while index + 12 <= len(content):
        size = struct.unpack('>I', content[index:index+4])[0]
        kind, end = content[index+4:index+8], index + 12 + size
        if end > len(content) or ended or not all(65 <= c <= 90 or 97 <= c <= 122 for c in kind) or kind[2] & 32:
            raise ValueError(error)
        value = content[index+8:index+8+size]
        if zlib.crc32(kind + value) & 0xffffffff != struct.unpack('>I', content[index+8+size:end])[0]:
            raise ValueError(error)
        if kind == b'IHDR':
            if header is not None or index != 8 or size != 13:
                raise ValueError(error)
            width, height, bits, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', value)
            if not (1 <= width <= 128 and 1 <= height <= 128 and bits in legal.get(color, ())
                    and compression == filtering == interlace == 0):
                # Interlaced source images are unsupported and use initials.
                raise ValueError(error)
            header = value
        elif header is None:
            raise ValueError(error)
        elif kind == b'PLTE':
            if palette is not None or image_data or transparency is not None or color in (0,4) or not size or size % 3 or size > 768:
                raise ValueError(error)
            if color == 3 and size // 3 > 2**bits:
                raise ValueError(error)
            palette = [tuple(value[i:i+3]) for i in range(0, size, 3)]
        elif kind == b'tRNS':
            if transparency is not None or image_data or color in (4,6):
                raise ValueError(error)
            if (color == 0 and size != 2) or (color == 2 and size != 6) or (color == 3 and (palette is None or not 1 <= size <= len(palette))):
                raise ValueError(error)
            transparency = value
            if color in (0,2) and any(v >= 2**bits for v in struct.unpack('>' + ('H' if color == 0 else 'HHH'), value)):
                raise ValueError(error)
        elif kind == b'IDAT':
            if data_closed or (color == 3 and palette is None):
                raise ValueError(error)
            image_data += value
        elif kind == b'IEND':
            if size or end != len(content):
                raise ValueError(error)
            ended = True
        elif not kind[0] & 32:
            raise ValueError(error)
        if image_data and kind != b'IDAT':
            data_closed = True
        index = end
    if header is None or not ended or not image_data:
        raise ValueError(error)
    channels = {0:1, 2:3, 3:1, 4:2, 6:4}[color]
    stride, bpp = (width * channels * bits + 7) // 8, max(1, (channels * bits + 7) // 8)
    expected = height * (stride + 1)
    decoder = zlib.decompressobj()
    try:
        pixels = decoder.decompress(image_data, expected + 1)
    except zlib.error:
        raise ValueError(error) from None
    if len(pixels) != expected or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
        raise ValueError(error)
    output, previous = bytearray(), bytearray(stride)
    transparent = (struct.unpack('>' + ('H' if color == 0 else 'HHH'), transparency)
                   if transparency is not None and color in (0,2) else None)
    def scale(value):
        return value * 255 // (2**bits - 1)
    def paeth(left, up, upper_left):
        guess = left + up - upper_left
        distances = (abs(guess-left), abs(guess-up), abs(guess-upper_left))
        return (left, up, upper_left)[distances.index(min(distances))]
    for row_index in range(height):
        position = row_index * (stride + 1)
        filter_type, row = pixels[position], bytearray(pixels[position+1:position+1+stride])
        if filter_type > 4:
            raise ValueError(error)
        for j in range(stride):
            left, up, upper_left = (row[j-bpp] if j >= bpp else 0), previous[j], (previous[j-bpp] if j >= bpp else 0)
            predictor = (0, left, up, (left+up)//2, paeth(left, up, upper_left))[filter_type]
            row[j] = (row[j] + predictor) & 255
        previous = row
        count = width * channels
        if bits == 16:
            samples = list(struct.unpack('>' + 'H' * count, row))
        elif bits == 8:
            samples = list(row)
        else:
            samples = [(row[(i*bits)//8] >> (8-bits-(i*bits)%8)) & (2**bits-1) for i in range(count)]
        output.append(0)
        for x in range(width):
            item = samples[x*channels:(x+1)*channels]
            if color == 0:
                gray = scale(item[0]); rgba = (gray,gray,gray,0 if tuple(item) == transparent else 255)
            elif color == 2:
                rgba = (*map(scale,item),0 if tuple(item) == transparent else 255)
            elif color == 3:
                if item[0] >= len(palette):
                    raise ValueError(error)
                alpha = transparency[item[0]] if transparency is not None and item[0] < len(transparency) else 255
                rgba = (*palette[item[0]],alpha)
            elif color == 4:
                gray = scale(item[0]); rgba = (gray,gray,gray,scale(item[1]))
            else:
                rgba = tuple(map(scale,item))
            output.extend(rgba)
    normalized = (b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))
                  + _chunk(b'IDAT',zlib.compress(bytes(output))) + _chunk(b'IEND',b''))
    if len(normalized) > MAX_IMAGE_BYTES:
        raise ValueError(error)
    return normalized


def public_payload(images=None):
    images = images or {}
    rows = []
    used = 0
    for code in all_codes():
        image = images.get(code)
        if image is not None:
            image = sanitize_png(image)
            text = PREFIX + base64.b64encode(image).decode('ascii')
            if used + len(text) > MAX_BUNDLE_BYTES - 65536:
                text = None
            else:
                used += len(text)
        else:
            text = None
        rows.append([code, text, 'WIKIDATA' if text else None])
    result = {'schema': SCHEMA, 'rows': rows}
    require_company_logos(result)
    return result


def require_company_logos(value):
    if not isinstance(value, dict) or set(value) != {'schema', 'rows'} or value['schema'] != SCHEMA:
        raise ValueError('LOGO_BUNDLE_INVALID')
    if not isinstance(value['rows'], list) or len(value['rows']) != len(all_codes()):
        raise ValueError('LOGO_BUNDLE_INVALID')
    for expected, row in zip(all_codes(), value['rows']):
        if not isinstance(row, list) or len(row) != 3 or row[0] != expected:
            raise ValueError('LOGO_BUNDLE_INVALID')
        if row[1] is None:
            if row[2] is not None:
                raise ValueError('LOGO_BUNDLE_INVALID')
        else:
            if row[2] != 'WIKIDATA' or not isinstance(row[1], str) or not row[1].startswith(PREFIX):
                raise ValueError('LOGO_BUNDLE_INVALID')
            try:
                content = base64.b64decode(row[1][len(PREFIX):], validate=True)
                if sanitize_png(content) != content:
                    raise ValueError('LOGO_BUNDLE_INVALID')
            except (ValueError, zlib.error):
                raise ValueError('LOGO_BUNDLE_INVALID') from None
    if len(json.dumps(value, separators=(',', ':')).encode()) > MAX_BUNDLE_BYTES:
        raise ValueError('LOGO_BUNDLE_OVERSIZED')
    return value
