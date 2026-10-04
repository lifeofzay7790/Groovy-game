#!/usr/bin/env bash
# Add models that the layout uses but Web/kit.json lacks, without rebuilding kit.json:
# packs them into Web/kit2.json (+ kit2_tex*.jpg), which the page loads next to kit.json.
#   BLENDER_PY    python with the bpy module
#   KIT_OUT_DIR   the folder given to KitProcessing/process_pieces.py for the new models (holds _preview/*.glb)
set -euo pipefail
cd "$(dirname "$0")"
rm -f build/kit.gltf build/player.gltf ../../Web/kit2_tex*.jpg     # split_gltf.py then only rewrites kit2
"$BLENDER_PY" pack_kit.py --new "$KIT_OUT_DIR"
npx --yes gltfpack@1.2.0 -i build/kit2_raw.glb -o build/kit2.gltf -kn -km
python3 split_gltf.py
python3 export_scene.py
