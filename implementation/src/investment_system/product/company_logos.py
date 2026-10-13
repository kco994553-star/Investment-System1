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


def sanitize_png(content: bytes) -> bytes:
    """Validate bounded PNG pixels, discard metadata and reject non-PNG content."""
    if not isinstance(content, bytes) or len(content) > MAX_IMAGE_BYTES or not content.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('LOGO_PNG_INVALID')
    index, chunks, image_data, header, ended = 8, [], b'', None, False
    while index + 12 <= len(content):
        size = struct.unpack('>I', content[index:index+4])[0]
        kind = content[index+4:index+8]
        end = index + 12 + size
        if end > len(content) or ended:
            raise ValueError('LOGO_PNG_INVALID')
        value = content[index+8:index+8+size]
        if zlib.crc32(kind + value) & 0xffffffff != struct.unpack('>I', content[index+8+size:end])[0]:
            raise ValueError('LOGO_PNG_INVALID')
        if kind == b'IHDR':
            if header is not None or index != 8 or size != 13:
                raise ValueError('LOGO_PNG_INVALID')
            width, height, bits, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', value)
            if not (1 <= width <= 128 and 1 <= height <= 128 and bits in (1,2,4,8,16) and color in (0,2,3,4,6)
                    and compression == filtering == 0 and interlace in (0,1)):
                raise ValueError('LOGO_PNG_INVALID')
            header = value
        elif kind == b'IDAT':
            image_data += value
        elif kind == b'IEND':
            if size or end != len(content):
                raise ValueError('LOGO_PNG_INVALID')
            ended = True
        elif kind not in (b'PLTE', b'tRNS') and not kind[0] & 32:
            raise ValueError('LOGO_PNG_INVALID')
        if kind in (b'IHDR', b'PLTE', b'tRNS', b'IDAT', b'IEND'):
            chunks.append(content[index:end])
        index = end
    if header is None or not ended or not image_data:
        raise ValueError('LOGO_PNG_INVALID')
    decoder = zlib.decompressobj()
    pixels = decoder.decompress(image_data, 128 * 128 * 8 + 2048)
    if decoder.unconsumed_tail or not decoder.eof or decoder.unused_data or not pixels:
        raise ValueError('LOGO_PNG_INVALID')
    return b'\x89PNG\r\n\x1a\n' + b''.join(chunks)


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
