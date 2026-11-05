"""Установка навыков агентов TROYA из пакета в Claude Code, Codex и Antigravity (Gemini).

Пакеты — папки рядом с «Установка»: 01_Конструктору_CAD (для всех конструкторов), 02_КТО_TROYA (только у владельца).
Ставятся все найденные пакеты. Каждый навык копируется целиком через подготовительную папку со сверкой SHA-256;
прежняя установленная копия сохраняется в <папка навыков агента>\\.skill-sync-backups\\<номер запуска>\\, при ошибке — откат.
Агент, которого нет на ПК (нет папки ~\\.claude, ~\\.codex или ~\\.gemini), пропускается.

  python install.py              показать, что изменится (ничего не пишет)
  python install.py --execute    установить
"""
import argparse
import sys
from pathlib import Path
from skill_sync_utils import synchronize, difference, differs

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ['01_Конструктору_CAD', '02_КТО_TROYA']
TARGETS = {
    'Claude Code': Path.home()/'.claude'/'skills',
    'Codex': Path.home()/'.codex'/'skills',
    'Antigravity (Gemini)': Path.home()/'.gemini'/'config'/'skills',
}


def skills():
    found = {}
    for pkg in PACKAGES:
        root = ROOT/pkg
        if root.is_dir():
            for p in sorted(root.iterdir()):
                if p.is_dir() and (p/'SKILL.md').is_file():
                    found[p.name] = p
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--execute', action='store_true', help='установить; без ключа — только показать план')
    args = parser.parse_args()
    found = skills()
    if not found:
        sys.exit('В %s нет пакетов навыков (%s)' % (ROOT, ', '.join(PACKAGES)))
    agents = {name: root for name, root in TARGETS.items() if root.parent.is_dir()}
    print('Пакет: %s\nНавыков: %d\nАгенты на этом ПК: %s' % (ROOT, len(found), ', '.join(agents) or 'нет'))
    if not agents:
        sys.exit('Не найден ни один агент (Claude Code, Codex, Antigravity).')
    pairs = [(src, root/name) for root in agents.values() for name, src in found.items()]
    for agent, root in agents.items():
        print('\n%s — %s' % (agent, root))
        for name, src in found.items():
            d = difference(src, root/name)
            state = ('новый' if not d['target_files'] else 'обновить') if differs(d) else 'без изменений'
            extra = '' if state != 'обновить' else ' (+%d / ~%d / −%d файлов)' % (len(d['added']), len(d['changed']), len(d['removed']))
            print('   %-40s %s%s' % (name, state, extra))
    if not args.execute:
        print('\nЭто план. Установить — python install.py --execute (или «Установить.cmd»).')
        return
    result = synchronize(pairs, execute=True, conflict_policy='source')
    changed = [p for p in result['plans'] if p.get('installed')]
    print('\nУстановлено или обновлено: %d; без изменений: %d.' % (len(changed), len(result['plans']) - len(changed)))
    if result.get('backups'):
        print('Прежние копии сохранены (%d), например: %s' % (len(result['backups']), result['backups'][0]))
    print('Перезапустите агентов, чтобы они увидели новые навыки.')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
