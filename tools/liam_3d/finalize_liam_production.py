"""Construye el GLB de produccion de LIAM con texturas PBR y animaciones."""
from math import sin
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/liam_3d/source/liam-completo-v1.blend"
OUTPUT = ROOT / "frontend/assets/lia/3d/liam-produccion-v1.glb"
EDITABLE = ROOT / "tools/liam_3d/source/liam-produccion-v1.blend"


def textile_image(name, size, base, strength, weave=False):
    image = bpy.data.images.new(name, width=size, height=size, alpha=True)
    pixels = [0.0] * (size * size * 4)
    for y in range(size):
        for x in range(size):
            if weave:
                pattern = (0.55 * sin(x * 0.78) + 0.45 * sin(y * 0.91)) * strength
                pattern += (1 if (x // 3 + y // 3) % 2 else -1) * strength * 0.22
            else:
                pattern = (sin(x * 0.19) + sin(y * 0.23)) * strength * 0.35
            offset = (y * size + x) * 4
            pixels[offset:offset + 4] = tuple(max(0.0, min(1.0, channel + pattern)) for channel in base) + (1.0,)
    image.pixels.foreach_set(pixels)
    image.pack()
    return image


def textured_material(material_name, image, roughness):
    material = bpy.data.materials.get(material_name)
    if material is None:
        raise RuntimeError(f"No se encontro el material {material_name}")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    principled = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    for input_name in ("Base Color", "Metallic", "Roughness"):
        for link in list(principled.inputs[input_name].links):
            links.remove(link)
    texture = next((node for node in nodes if node.type == "TEX_IMAGE"), None) or nodes.new("ShaderNodeTexImage")
    texture.name = f"{material_name} embedded texture"
    texture.image = image
    links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Roughness"].default_value = roughness


if not SOURCE.exists():
    raise RuntimeError(f"No existe la fuente animada: {SOURCE}")
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

# Primitivas, camaras y luces heredadas alteraban el encuadre automatico.
for obj in list(bpy.context.scene.objects):
    helper = obj.type in {"CAMERA", "LIGHT"}
    primitive = obj.type == "MESH" and obj.name in {"Cube", "Icosphere"}
    if helper or primitive:
        bpy.data.objects.remove(obj, do_unlink=True)
for armature in (obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"):
    for pose_bone in armature.pose.bones:
        pose_bone.custom_shape = None

textured_material("LIAM Navy", textile_image("LIAM_navy_textile_512", 512, (0.018, 0.075, 0.19), 0.012, True), 0.72)
textured_material("LIAM Blouse", textile_image("LIAM_white_textile_512", 512, (0.84, 0.89, 0.94), 0.018, True), 0.78)
textured_material("LIAM fitted formal shoes", textile_image("LIAM_shoe_leather_256", 256, (0.012, 0.019, 0.035), 0.008), 0.42)
textured_material("LIAM Cyan", textile_image("LIAM_cyan_accent_128", 128, (0.0, 0.55, 0.82), 0.006), 0.38)

# Normalizar PBR y empacar todos los mapas, incluidos piel, rostro y cabello.
for material in bpy.data.materials:
    if not material.use_nodes:
        continue
    principled = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if principled is None:
        continue
    for input_name in ("Metallic", "Roughness"):
        for link in list(principled.inputs[input_name].links):
            material.node_tree.links.remove(link)
    principled.inputs["Metallic"].default_value = 0.0
    if material.name not in {"LIAM Navy", "LIAM Blouse", "LIAM fitted formal shoes", "LIAM Cyan"}:
        principled.inputs["Roughness"].default_value = 0.88 if "afro" in material.name.lower() else 0.64
    for node in material.node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image:
            limit = 512 if "afro" in material.name.lower() else 2048
            if max(node.image.size) > limit:
                scale = limit / max(node.image.size)
                node.image.scale(max(1, round(node.image.size[0] * scale)), max(1, round(node.image.size[1] * scale)))
            node.image.pack()

required_actions = {"Idle", "Walk", "Wave", "Point", "Talk", "Listen", "Think"}
missing = required_actions.difference(bpy.data.actions.keys())
if missing:
    raise RuntimeError(f"Faltan animaciones: {sorted(missing)}")

EDITABLE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(EDITABLE))
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(OUTPUT), export_format="GLB", use_selection=True,
    export_animations=True, export_nla_strips=True, export_apply=True, export_yup=True,
    export_materials="EXPORT", export_image_format="JPEG", export_image_quality=84,
    export_armature_object_remove=True, export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6)
print(f"LIAM_PRODUCTION={OUTPUT} bytes={OUTPUT.stat().st_size}")
print(f"LIAM_EDITABLE={EDITABLE}")
