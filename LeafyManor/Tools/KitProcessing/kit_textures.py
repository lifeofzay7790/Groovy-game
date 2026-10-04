"""Write the kit texture set for a Tripo GLB sheet (textures embedded in the GLB).

usage: python kit_textures.py <sheet.glb> <Sheet> [size]
Writes LeafyManor/Models/Textures/T_LM_Kit_<Sheet>_BaseColor.jpg, _Normal.png (DirectX green) and _ORM.jpg
(R = AO, G = Roughness, B = Metallic; Tripo's metallicRoughness map already uses this layout), at `size` px (4096).
"""
import io
import json
import os
import struct
import sys

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None
glb, sheet = sys.argv[1], sys.argv[2]
size = int(sys.argv[3]) if len(sys.argv) > 3 else 4096
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Models", "Textures")

with open(glb, "rb") as f:
    f.read(12)
    n, _ = struct.unpack("<II", f.read(8))
    gl = json.loads(f.read(n))
    n, _ = struct.unpack("<II", f.read(8))
    blob = f.read(n)


def image(tex_index):
    bv = gl["bufferViews"][gl["images"][gl["textures"][tex_index]["source"]]["bufferView"]]
    off = bv.get("byteOffset", 0)
    im = Image.open(io.BytesIO(blob[off:off + bv["byteLength"]])).convert("RGB")
    return im.resize((size, size), Image.LANCZOS) if im.size != (size, size) else im


m = gl["materials"][0]
base = image(m["pbrMetallicRoughness"]["baseColorTexture"]["index"])
orm = image(m["pbrMetallicRoughness"]["metallicRoughnessTexture"]["index"])
r, g, b = image(m["normalTexture"]["index"]).split()
normal = Image.merge("RGB", (r, ImageOps.invert(g), b))          # OpenGL (glTF) -> DirectX (Unreal)
stem = os.path.join(OUT, "T_LM_Kit_%s_" % sheet)
base.save(stem + "BaseColor.jpg", quality=90)
orm.save(stem + "ORM.jpg", quality=92)
normal.save(stem + "Normal.png", optimize=True)
print("wrote", stem + "{BaseColor.jpg, ORM.jpg, Normal.png}")
