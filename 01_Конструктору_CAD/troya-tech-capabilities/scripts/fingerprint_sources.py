"""Pin source file identities without inventing document revision numbers."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent


def default_source_dir():
    """Production sources remain outside the agent skill library."""
    pinned = json.loads((SKILL / 'data' / 'source_fingerprints.json').read_text(encoding='utf-8'))
    return Path(pinned['source_directory'])


def fingerprint(root):
    if not root.is_dir():
        raise FileNotFoundError(root)
    rows=[]
    for path in sorted(root.iterdir()):
        if path.is_file():
            rows.append(dict(file=path.name,bytes=path.stat().st_size,
                             sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             document_revision=None,revision_status='Номер ревизии документа не установлен'))
    return dict(fingerprinted_at=datetime.now(timezone.utc).isoformat(),source_directory=str(root),
                note='SHA256 фиксирует конкретную копию; не подтверждает трактовку характеристик или дату ревизии паспорта.',
                sources=rows)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir',type=Path,default=default_source_dir())
    args=ap.parse_args()
    data=fingerprint(args.source_dir)
    target=SKILL/'data'/'source_fingerprints.json'
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Pinned {len(data["sources"])} source files: {target}')


if __name__ == '__main__':
    main()
