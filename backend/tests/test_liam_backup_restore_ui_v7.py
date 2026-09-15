from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
controller=(ROOT/'frontend'/'js'/'liam'/'liam-controller.js').read_text(encoding='utf-8')
index=(ROOT/'frontend'/'index.html').read_text(encoding='utf-8')
block=controller[controller.index('if (handler === "restore_backup")'):controller.index('throw new Error("La acción protegida',controller.index('if (handler === "restore_backup")'))]
assert "prompt('Confirma tu identidad" in block
assert "/api/backups/${Number(a.backup_id)}/restaurar" in block
assert "confirmar:'RESTAURAR',password_actual:passwordActual" in block
assert '/api/asistente-capacitacion' not in block
assert 'liam-controller.js?v=2.7.5-backup-restore-1' in index
print('LIAM_BACKUP_RESTORE_UI_V7_PASS')
