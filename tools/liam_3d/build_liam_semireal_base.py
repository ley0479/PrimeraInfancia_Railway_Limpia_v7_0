"""Genera la base anatómica semirrealista de LIAM con MPFB (activos CC0)."""
import bpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "tools" / "liam_3d" / "work"
WORK.mkdir(parents=True, exist_ok=True)

if not hasattr(bpy.ops, "mpfb") or not hasattr(bpy.ops.mpfb, "create_human"):
    try:
        bpy.ops.preferences.addon_enable(module="bl_ext.blender_org.mpfb")
    except Exception as exc:
        raise RuntimeError("MPFB no está habilitado en Blender") from exc

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
settings = {
    "MPFB_NH_scale_factor": "METER",
    "MPFB_NH_add_phenotype": True,
    "MPFB_NH_phenotype_gender": "female",
    "MPFB_NH_phenotype_age": "young",
    "MPFB_NH_phenotype_race": "african",
    "MPFB_NH_phenotype_muscle": "averagemuscle",
    "MPFB_NH_phenotype_weight": "averageweight",
    "MPFB_NH_phenotype_height": "average",
    "MPFB_NH_phenotype_proportions": "average",
    "MPFB_NH_phenotype_influence": 0.72,
    "MPFB_NH_add_breast": True,
    "MPFB_NH_phenotype_breastsize": "mincup",
    "MPFB_NH_phenotype_breastfirmness": "maxfirmness",
    "MPFB_NH_breast_influence": 0.30,
    "MPFB_NH_detailed_helpers": False,
    "MPFB_NH_extra_vertex_groups": True,
    "MPFB_NH_mask_helpers": True,
}
missing=[]
for name, value in settings.items():
    if not hasattr(scene, name):
        missing.append(name)
    else:
        setattr(scene, name, value)
if missing:
    raise RuntimeError(f"Propiedades MPFB ausentes: {missing}")

result=bpy.ops.mpfb.create_human()
if "FINISHED" not in result:
    raise RuntimeError(f"MPFB no creó la base: {result}")

base=bpy.context.active_object
base.name="LIAM_Semireal_Base"
base["liam_stage"]="semireal_base"
base["liam_license"]="CC0-1.0 assets generated with MPFB"

for polygon in base.data.polygons:
    polygon.use_smooth=True

scene.MPFB_ADR_standard_rig="game_engine"
scene.MPFB_ADR_import_weights=True
bpy.context.view_layer.objects.active=base
base.select_set(True)
rig_result=bpy.ops.mpfb.add_standard_rig()
if "FINISHED" not in rig_result:
    raise RuntimeError(f"MPFB no creó el rig: {rig_result}")
rig=next((obj for obj in bpy.context.scene.objects if obj.type=="ARMATURE"),None)
if rig is None:
    raise RuntimeError("El rig de juego no apareció en la escena")
rig.name="LIAM_Game_Rig"

path=WORK / "liam-semireal-base-v1.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(path))
print(f"LIAM_SEMIREAL_BASE={path}")
print(f"LIAM_SEMIREAL_GEOMETRY vertices={len(base.data.vertices)} polygons={len(base.data.polygons)} shape_keys={len(base.data.shape_keys.key_blocks) if base.data.shape_keys else 0}")
print(f"LIAM_SEMIREAL_RIG bones={len(rig.data.bones)} vertex_groups={len(base.vertex_groups)}")
