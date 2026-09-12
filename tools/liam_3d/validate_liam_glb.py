import bpy
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
model = Path(args[0]).resolve() if args else root / "frontend/assets/lia/3d/liam-produccion-v1.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(model))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
triangles = 0
for obj in meshes:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    triangles += len(mesh.loop_triangles)
    evaluated.to_mesh_clear()
actions = sorted(action.name for action in bpy.data.actions)
assert meshes, "El GLB no contiene mallas"
assert armatures, "El GLB no contiene armature"
assert set(("Idle", "Walk", "Wave", "Point", "Talk", "Listen", "Think")).issubset(actions), actions
assert model.stat().st_size <= 10_000_000, f"GLB demasiado pesado: {model.stat().st_size} bytes"
names = {obj.name for obj in meshes}
assert "LIAM FaceBuilder head" in names, names
assert "LIAM optimized natural afro" in names, names
assert "LIAM fitted formal flats" in names, names
head = bpy.data.objects["LIAM FaceBuilder head"]
hair = bpy.data.objects["LIAM optimized natural afro"]
assert head.parent in armatures and head.parent_type == "BONE", "La cabeza no sigue el armature"
assert hair.parent in armatures and hair.parent_type == "BONE", "El afro no sigue el armature"
assert head.parent_bone == "head" and hair.parent_bone == "head"
print(f"LIAM_GLB_VALID meshes={len(meshes)} armatures={len(armatures)} triangles={triangles} actions={actions}")
