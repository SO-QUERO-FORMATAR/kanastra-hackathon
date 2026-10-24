"""Verify deterministic regeneration without silently accepting changed integration contracts."""
import hashlib
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
paths=[*sorted((root/'docs/contratos').glob('*')),root/'docs/handoff-frontend.md']
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
for script in ['gerar_contrato_api.py','gerar_handoff_frontend.py','validar_contrato_api.py']:
    subprocess.run([sys.executable,str(root/'scripts'/script)],check=True)
after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
if before!=after:
    raise SystemExit('Regeneração modificou artefatos: revise o diff; não houve atualização silenciosa.')
print('Regeneração determinística: contratos e handoff idênticos byte a byte.')
