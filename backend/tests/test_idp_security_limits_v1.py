from pathlib import Path
import tempfile
import zipfile

from modules.idp_documental.services import validate_file_signature


def rejected(path, message):
    try:
        validate_file_signature(path)
    except ValueError:
        return
    raise AssertionError(message)


with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    traversal=root/'traversal.docx'
    with zipfile.ZipFile(traversal,'w') as archive:
        archive.writestr('../fuera.xml','contenido')
    rejected(traversal,'Aceptó traversal dentro de Office.')

    bomb=root/'ratio.docx'
    with zipfile.ZipFile(bomb,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('word/document.xml','0'*(2*1024*1024))
    rejected(bomb,'Aceptó una relación de compresión abusiva.')

    invalid=root/'falso.pdf';invalid.write_bytes(b'NO ES PDF')
    rejected(invalid,'Aceptó un PDF sin firma válida.')

print('IDP_SECURITY_LIMITS_V1_PASS')
