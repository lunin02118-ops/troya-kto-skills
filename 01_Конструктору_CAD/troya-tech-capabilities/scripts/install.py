"""Install canonical TROYA skill using staged copies, SHA verification and backups."""
import argparse
import json
from pathlib import Path
from skill_sync_utils import synchronize

SRC = Path(__file__).resolve().parent.parent
NAME = SRC.name
TARGETS = {
    'Claude Code': Path.home()/'.claude'/'skills',
    'Antigravity': Path.home()/'.gemini'/'config'/'skills',
    'Codex': Path.home()/'.codex'/'skills',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Install; otherwise compare only')
    parser.add_argument('--conflict-policy', choices=['abort','source'], default='abort')
    args = parser.parse_args()
    pairs = [(SRC, root/NAME) for root in TARGETS.values() if root.parent.is_dir() and root/NAME != SRC]
    result = synchronize(pairs,execute=args.execute,conflict_policy=args.conflict_policy)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
