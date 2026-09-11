"""Construye LIAM v5 sobre la base MPFB, lista para revisión y exportación web."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "tools" / "liam_3d" / "work"
OUT = ROOT / "frontend" / "assets" / "lia" / "3d"
SOURCE = ROOT / "tools" / "liam_3d" / "source"
BASE = WORK / "liam-semireal-base-v1.blend"
SKIN_MHMAT = Path.home() / "AppData/Roaming/Blender Foundation/Blender/5.2/extensions/.user/blender_org/mpfb/data/skins/young_african_female/young_african_female.mhmat"
SKIN_TEXTURE = SKIN_MHMAT.parent / "young_darkskinned_female_diffuse.png"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(parents=True, exist_ok=True)


def material(name, rgb, roughness=0.55, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def select_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def smooth(obj):
    if obj.type == "MESH":
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def shell_from_body(body, name, predicate, mat, offset=0.008):
    """Duplica solo caras del cuerpo; conserva pesos y modificador del rig."""
    obj = body.copy()
    obj.data = body.data.copy()
    obj.animation_data_clear()
    obj.name = name
    bpy.context.collection.objects.link(obj)
    select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    keep = []
    for poly in obj.data.polygons:
        center = sum((obj.data.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)
        if predicate(center):
            keep.append(poly.index)
    for poly in obj.data.polygons:
        poly.select = poly.index not in keep
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    decimate = obj.modifiers.new("Web geometry reduction", "DECIMATE")
    decimate.ratio = 0.42
    solid = obj.modifiers.new("Tailored thickness", "SOLIDIFY")
    solid.thickness = offset
    solid.offset = 1.0
    return smooth(obj)


def uv(name, loc, scale, mat, segments=16, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return smooth(obj)


def cube(name, loc, scale, mat, bevel=0.01):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    mod = obj.modifiers.new("Tailoring", "BEVEL")
    mod.width, mod.segments = bevel, 2
    return obj


def parent_to_bone(obj, armature, bone_name):
    """Enlaza sin alterar la posición mundial calculada para el accesorio."""
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world


bpy.ops.wm.open_mainfile(filepath=str(BASE))
body = bpy.data.objects["LIAM_Semireal_Base"]
rig = bpy.data.objects["LIAM_Game_Rig"]
body["liam_stage"] = "semireal_web_candidate_v5"

# Abrir el .blend reemplaza todos los datablocks; los materiales deben crearse después.
NAVY = material("LIAM Navy", (0.012, 0.035, 0.095), 0.62)
WHITE = material("LIAM Blouse", (0.92, 0.95, 0.98), 0.7)
BLACK = material("LIAM Hair", (0.006, 0.008, 0.012), 0.82)
SHOE = material("LIAM Shoes", (0.008, 0.012, 0.022), 0.3)
CYAN = material("LIAM Cyan", (0.0, 0.58, 0.86), 0.3, 0.1)
EYEWHITE = material("LIAM Eye White", (0.88, 0.9, 0.87), 0.28)
IRIS = material("LIAM Iris", (0.075, 0.026, 0.012), 0.35)
LIP = material("LIAM Lip", (0.24, 0.035, 0.055), 0.48)

# Material de piel oficial CC0 de MakeHuman.
select_only(body)
if SKIN_MHMAT.exists():
    result = bpy.ops.mpfb.load_library_material(filepath=str(SKIN_MHMAT))
    if "FINISHED" not in result:
        raise RuntimeError(f"No se pudo cargar la piel: {result}")

# MPFB usa una red rica con varias texturas que glTF puede interpretar de forma
# ambigua. Para web se conserva un único mapa difuso, evitando artefactos faciales.
if not SKIN_TEXTURE.exists() or not body.data.materials:
    raise RuntimeError("No se encontró la textura difusa de piel instalada")
skin_material = body.data.materials[0]
skin_material.use_nodes = True
skin_nodes = skin_material.node_tree.nodes
skin_nodes.clear()
skin_output = skin_nodes.new("ShaderNodeOutputMaterial")
skin_bsdf = skin_nodes.new("ShaderNodeBsdfPrincipled")
skin_bsdf.inputs["Roughness"].default_value = 0.58
skin_image_node = skin_nodes.new("ShaderNodeTexImage")
skin_image = bpy.data.images.load(str(SKIN_TEXTURE), check_existing=True)
if max(skin_image.size) > 1024:
    skin_image.scale(1024, 1024)
skin_image_node.image = skin_image
skin_material.node_tree.links.new(skin_image_node.outputs["Color"], skin_bsdf.inputs["Base Color"])
skin_material.node_tree.links.new(skin_bsdf.outputs["BSDF"], skin_output.inputs["Surface"])

# Consolidar la forma antropométrica y reducir geometría/imagen para web.
select_only(body)
if body.data.shape_keys:
    bpy.ops.object.shape_key_remove(all=True, apply_mix=True)

# Prendas derivadas de la propia topología: se deforman con los 53 huesos.
trousers = shell_from_body(body, "LIAM tailored trousers", lambda c: 0.06 < c.z < 0.91 and c.y < 0.085, NAVY, 0.012)
blouse = shell_from_body(body, "LIAM white blouse", lambda c: 0.90 < c.z < 1.36 and abs(c.x) < 0.29 and c.y < 0.07, WHITE, 0.009)
blazer = shell_from_body(
    body,
    "LIAM executive blazer",
    lambda c: 0.88 < c.z < 1.38 and c.y < 0.08 and (abs(c.x) > 0.14 or c.y > -0.12),
    NAVY,
    0.018,
)

# Ocultar bajo la ropa reduce sobre-dibujo sin destruir la base editable.
body["liam_clothing_occlusion"] = "body retained for non-destructive source; web export prunes hidden geometry later"

# Zapatos y detalles institucionales.
for side, x in (("L", -0.105), ("R", 0.105)):
    shoe = cube(f"Formal shoe {side}", (x, -0.09, 0.045), (0.078, 0.145, 0.043), SHOE, 0.022)
    parent_to_bone(shoe, rig, f"foot_{side.lower()}")
badge = cube("LIAM badge", (0.17, -0.205, 1.225), (0.055, 0.006, 0.026), WHITE, 0.006)
parent_to_bone(badge, rig, "spine_03")
accent = cube("LIAM badge cyan", (0.126, -0.213, 1.225), (0.006, 0.004, 0.019), CYAN, 0.003)
parent_to_bone(accent, rig, "spine_03")

# Afro de silueta agrupada, mucho más liviano que cabello por hebras.
hair_points = [
    (-.14, .01, 1.65), (-.05, .00, 1.71), (.05, .00, 1.71), (.14, .01, 1.65),
    (-.205, .025, 1.57), (.205, .025, 1.57), (-.205, .055, 1.48), (.205, .055, 1.48),
    (-.13, .095, 1.70), (0, .10, 1.72), (.13, .095, 1.70),
    (-.145, .12, 1.54), (0, .135, 1.61), (.145, .12, 1.54),
]
for index, point in enumerate(hair_points):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=.095, location=point)
    hair = smooth(bpy.context.object)
    hair.name = f"Afro volume {index:02d}"
    hair.data.materials.append(BLACK)
    parent_to_bone(hair, rig, "head")

# Boca articulada compacta. La textura aporta los ojos; duplicarlos produciría mirada artificial.
select_only(rig)
bpy.ops.object.mode_set(mode="EDIT")
jaw = rig.data.edit_bones.new("jaw")
jaw.head, jaw.tail = (0, -.255, 1.51), (0, -.31, 1.47)
jaw.parent = rig.data.edit_bones["head"]
bpy.ops.object.mode_set(mode="OBJECT")
mouth = uv("LIAM animated lips", (0, -.326, 1.485), (.026, .006, .006), LIP, 16, 8)
mouth.parent = rig
mouth.matrix_parent_inverse = rig.matrix_world.inverted()
mouth_group = mouth.vertex_groups.new(name="jaw")
mouth_group.add(range(len(mouth.data.vertices)), 1.0, "REPLACE")
mouth_armature = mouth.modifiers.new("Jaw deformation", "ARMATURE")
mouth_armature.object = rig


def action(name, end, rotations, locations=None):
    act = bpy.data.actions.new(name)
    act.frame_start, act.frame_end = 1, end
    rig.animation_data_create()
    rig.animation_data.action = act
    for bone_name, keys in rotations.items():
        bone = rig.pose.bones[bone_name]
        bone.rotation_mode = "XYZ"
        for frame, value in keys:
            bone.rotation_euler = value
            bone.keyframe_insert("rotation_euler", frame=frame, group=bone_name)
    for bone_name, keys in (locations or {}).items():
        bone = rig.pose.bones[bone_name]
        for frame, value in keys:
            bone.location = value
            bone.keyframe_insert("location", frame=frame, group=bone_name)
    track = rig.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 1, act)
    strip.action_frame_start, strip.action_frame_end = 1, end
    rig.animation_data.action = None


# Acciones corporales naturales; el rostro usa jaw/head y parpadeo en la siguiente fase.
action("Idle", 90, {
    "spine_02": [(1, (0, 0, 0)), (45, (.018, 0, 0)), (90, (0, 0, 0))],
    "head": [(1, (0, 0, -.025)), (45, (0, 0, .025)), (90, (0, 0, -.025))],
})
action("Wave", 56, {
    "upperarm_r": [(1, (0, 0, 0)), (12, (-.25, -.1, -1.35)), (56, (-.25, -.1, -1.35))],
    "lowerarm_r": [(1, (0, 0, 0)), (12, (0, 0, -1.4)), (23, (0, 0, -.75)), (34, (0, 0, -1.4)), (45, (0, 0, -.75)), (56, (0, 0, -1.4))],
})
action("Point", 48, {
    "upperarm_r": [(1, (0, 0, 0)), (20, (-.1, -1.15, -1.05)), (48, (-.1, -1.15, -1.05))],
    "lowerarm_r": [(1, (0, 0, 0)), (20, (0, 0, .12)), (48, (0, 0, .12))],
    "head": [(1, (0, 0, 0)), (20, (0, .1, -.1)), (48, (0, .1, -.1))],
})
action("Talk", 72, {
    "head": [(1, (0, 0, -.02)), (24, (.025, 0, .025)), (48, (-.018, 0, -.02)), (72, (0, 0, .02))],
    "upperarm_l": [(1, (0, 0, 0)), (36, (0, .08, .18)), (72, (0, 0, 0))],
    "upperarm_r": [(1, (0, 0, 0)), (36, (0, -.08, -.18)), (72, (0, 0, 0))],
    "jaw": [(1, (0, 0, 0)), (8, (.10, 0, 0)), (16, (.025, 0, 0)), (25, (.14, 0, 0)), (34, (.04, 0, 0)), (44, (.12, 0, 0)), (54, (.02, 0, 0)), (64, (.11, 0, 0)), (72, (0, 0, 0))],
})
action("Listen", 60, {"head": [(1, (0, 0, 0)), (20, (0, .06, -.08)), (50, (0, .06, -.08)), (60, (0, 0, 0))]})
action("Think", 72, {
    "head": [(1, (0, 0, 0)), (24, (0, -.08, .11)), (60, (0, -.08, .11)), (72, (0, 0, 0))],
    "upperarm_r": [(1, (0, 0, 0)), (24, (0, -.2, -.35)), (60, (0, -.2, -.35)), (72, (0, 0, 0))],
    "lowerarm_r": [(1, (0, 0, 0)), (24, (0, 0, -1.15)), (60, (0, 0, -1.15)), (72, (0, 0, 0))],
})
action("Walk", 48, {
    "thigh_l": [(1, (.38, 0, 0)), (24, (-.38, 0, 0)), (48, (.38, 0, 0))],
    "thigh_r": [(1, (-.38, 0, 0)), (24, (.38, 0, 0)), (48, (-.38, 0, 0))],
    "calf_l": [(1, (0, 0, 0)), (24, (.3, 0, 0)), (48, (0, 0, 0))],
    "calf_r": [(1, (.3, 0, 0)), (24, (0, 0, 0)), (48, (.3, 0, 0))],
})

# La revisión se renderiza en pose neutra, no con todas las pistas NLA sumadas.
for track in rig.animation_data.nla_tracks:
    track.mute = True
for pose_bone in rig.pose.bones:
    pose_bone.rotation_mode = "XYZ"
    pose_bone.rotation_euler = (0, 0, 0)
    pose_bone.location = (0, 0, 0)
bpy.context.view_layer.update()

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world.color = (0.018, 0.024, 0.045)
bpy.ops.object.camera_add(location=(0, -4.7, 1.18))
camera = bpy.context.object
camera.data.lens = 62
camera.rotation_euler = ((Vector((0, 0, .9)) - camera.location).to_track_quat("-Z", "Y").to_euler())
scene.camera = camera
bpy.ops.object.light_add(type="AREA", location=(-2.2, -3.2, 3.2))
bpy.context.object.data.energy, bpy.context.object.data.shape, bpy.context.object.data.size = 1100, "DISK", 4.0
bpy.context.object.rotation_euler = ((Vector((0, 0, 1.05)) - bpy.context.object.location).to_track_quat("-Z", "Y").to_euler())
bpy.ops.object.light_add(type="AREA", location=(2.2, -1.4, 2.0))
bpy.context.object.data.energy, bpy.context.object.data.color, bpy.context.object.data.size = 650, (0.25, .72, 1.0), 3.0
bpy.context.object.rotation_euler = ((Vector((0, 0, 1.0)) - bpy.context.object.location).to_track_quat("-Z", "Y").to_euler())

preview = OUT / "liam-semireal-v5-preview.png"
blend = SOURCE / "liam-semireal-v5.blend"
glb = OUT / "liam-semireal-v5.glb"
scene.render.filepath = str(preview)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))

# Quitar objetos de revisión antes de exportar y conservar solo recursos empacados.
for obj in [o for o in scene.objects if o.type in {"CAMERA", "LIGHT"}]:
    bpy.data.objects.remove(obj, do_unlink=True)
for track in rig.animation_data.nla_tracks:
    track.mute = False
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=str(glb), export_format="GLB", use_selection=True,
    export_animations=True, export_nla_strips=True,
    export_apply=True, export_yup=True,
)
triangles = sum(len(p.vertices) - 2 for o in scene.objects if o.type == "MESH" for p in o.data.polygons)
print(f"LIAM_SEMIREAL_V5 preview={preview}")
print(f"LIAM_SEMIREAL_V5 blend={blend}")
print(f"LIAM_SEMIREAL_V5 glb={glb} bytes={glb.stat().st_size} triangles={triangles}")
