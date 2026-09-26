"""build/{kit,player}.gltf+.bin (gltfpack output) -> Web/*.json (geometry embedded as base64) + separate .jpg textures."""
import base64, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'build')
WEB = os.path.join(HERE, '..', '..', 'Web')
for n in ('kit', 'player'):
    j = json.load(open(os.path.join(D, n + '.gltf')))
    bin_ = open(os.path.join(D, n + '.bin'), 'rb').read()
    views = j['bufferViews']
    img_views = set()
    for k, im in enumerate(j.get('images', [])):
        v = views[im['bufferView']]
        data = bin_[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]
        name = '%s_tex%d.jpg' % (n, k)
        open(os.path.join(WEB, name), 'wb').write(data)
        img_views.add(im.pop('bufferView'))
        im.pop('mimeType', None)
        im['uri'] = name
    remap, out, new_views = {}, bytearray(), []
    for k, v in enumerate(views):
        if k in img_views:
            continue
        while len(out) % 4:
            out.append(0)
        o = v.get('byteOffset', 0)
        nv = dict(v, buffer=0, byteOffset=len(out))
        out += bin_[o:o + v['byteLength']]
        remap[k] = len(new_views)
        new_views.append(nv)
    for a in j['accessors']:
        if 'bufferView' in a:
            a['bufferView'] = remap[a['bufferView']]
    j['bufferViews'] = new_views
    j['buffers'] = [dict(byteLength=len(out), uri='data:application/octet-stream;base64,' + base64.b64encode(bytes(out)).decode())]
    json.dump(j, open(os.path.join(WEB, n + '.json'), 'w'), separators=(',', ':'))
    print(n, 'geometry', len(out), 'json', os.path.getsize(os.path.join(WEB, n + '.json')), 'textures', len(img_views))
