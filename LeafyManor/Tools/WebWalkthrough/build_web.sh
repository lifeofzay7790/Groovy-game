#!/usr/bin/env bash
# Rebuild LeafyManor/Web (the browser walkthrough) from the kit and the layout.
#   BLENDER_PY    python with the bpy module (e.g. a venv with `pip install bpy`)
#   KIT_OUT_DIR   the folder given to KitProcessing/process_pieces.py (holds _preview/*.glb)
#   PLAYER_FBX / PLAYER_TEX   your character FBX and its base-colour texture
# Needs Node for `npx gltfpack`.
set -euo pipefail
cd "$(dirname "$0")"
"$BLENDER_PY" pack_kit.py "$KIT_OUT_DIR"
"$BLENDER_PY" pack_char.py "$PLAYER_FBX" "$PLAYER_TEX"
npx --yes gltfpack@1.2.0 -i build/kit_raw.glb -o build/kit.gltf -kn -km
npx --yes gltfpack@1.2.0 -i build/player_raw.glb -o build/player.gltf -kn -km
python3 split_gltf.py
python3 export_scene.py
