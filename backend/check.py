"""Run accumulated regression and retain stage evidence. From backend/: uv run python check.py T01 green."""
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf8')
stage, phase = sys.argv[1:3]
report = Path('../docs/execucao')
report.mkdir(exist_ok=True)
command = [sys.executable, '-m', 'pytest', '-q', f'--junitxml={report}/{stage}-{phase}.xml', *sys.argv[3:]]
result = subprocess.run(command, capture_output=True, text=True, encoding='utf8', errors='replace')
(report / f'{stage}-{phase}.txt').write_text(' '.join(command) + '\n' + result.stdout + result.stderr, encoding='utf8')
print(result.stdout)
print(result.stderr)
sys.exit(result.returncode)

