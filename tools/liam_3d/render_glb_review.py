"""Reimporta el GLB entregable y genera evidencia visual de la salida real."""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

root = Path(__file__).resolve().parents[2]
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
model = Path(args[0]).resolve() if args else root / "frontend/assets/lia/3d/liam-semireal-v5.glb"
output = Path(args[1]).resolve() if len(args) > 1 else root / "tools/liam_3d/work/liam-glb-review.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(model))
for armature in (obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"):
    armature.data.pose_position = "REST"

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world = scene.world or bpy.data.worlds.new("LIAM review world")
scene.world.color = (0.018, 0.024, 0.045)

bpy.ops.object.camera_add(location=(0, -4.7, 1.18))
camera = bpy.context.object
camera.data.lens = 62
camera.rotation_euler = ((Vector((0, 0, .9)) - camera.location).to_track_quat("-Z", "Y").to_euler())
scene.camera = camera
for location, energy, color, size in (
    ((-2.2, -3.2, 3.2), 1100, (1, 1, 1), 4.0),
    ((2.2, -1.4, 2.0), 650, (.25, .72, 1.0), 3.0),
):
    bpy.ops.object.light_add(type="AREA", location=location)
    lamp = bpy.context.object
    lamp.data.energy, lamp.data.color, lamp.data.size = energy, color, size
    lamp.rotation_euler = ((Vector((0, 0, 1.0)) - lamp.location).to_track_quat("-Z", "Y").to_euler())

output.parent.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(output)
bpy.ops.render.render(write_still=True)
print(f"LIAM_GLB_REVIEW={output}")
