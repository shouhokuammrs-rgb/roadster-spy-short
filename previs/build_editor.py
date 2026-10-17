"""editor_src.html + blocking.json + rig/ → editor.html (single self-contained file for the artifact).
usage: python3 build_editor.py"""
import base64, json, os
H = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(H, "editor_src.html")).read()
blocking = open(os.path.join(H, "blocking.json")).read()
baked = json.load(open(os.path.join(H, "rig", "poses_baked.json")))["poses"]
posegun = json.dumps({k: v["gun"] for k, v in baked.items()})
glb = base64.b64encode(open(os.path.join(H, "rig", "mannequin.glb"), "rb").read()).decode()
out = src.replace("__BLOCKING__", blocking).replace("__POSEGUN__", posegun).replace("__MANNEQUIN__", glb)
open(os.path.join(H, "editor.html"), "w").write(out)
print("editor.html", len(out) // 1024, "KB")
