"""Проверка сценария схемы сборки (JSON) для вёрстки и веб-просмотра.

Только читает файл: CAD не открывает, ничего не меняет, сторонних библиотек не требует.

Запуск:
    python validate_scenario.py <сценарий.json> [--output отчёт.json]

Код выхода: 0 — сценарий годен, 1 — есть ошибки (список в отчёте).

Проверяет: id деталей, габариты, оси, количества, фазы, номера шагов, ссылки
шагов на детали и комплект, статус «утверждено» при открытых вопросах.
Не проверяет: доступ рук и инструмента, выбор отверстия, настоящие размеры и
физический порядок сборки — это смотрят по модели и глазами.
"""
import argparse
import json
import math
import sys
from pathlib import Path


def validate(guide):
    errors = []
    warnings = []

    def need(condition, message):
        if not condition:
            errors.append(message)

    def number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)

    def vector(v):
        return isinstance(v, list) and len(v) == 3 and all(number(x) for x in v)

    def quantity(v):
        return isinstance(v, int) and not isinstance(v, bool) and v > 0

    if not isinstance(guide, dict):
        return {'valid': False, 'errors': ['Сценарий должен быть объектом JSON.'], 'warnings': []}
    parts = guide.get('parts', [])
    steps = guide.get('steps', [])
    inventory = guide.get('inventory', [])
    if not all(isinstance(x, list) for x in [parts, steps, inventory]):
        return {'valid': False, 'errors': ['parts, steps и inventory должны быть списками.'], 'warnings': []}
    if not all(isinstance(x, dict) for x in parts + steps + inventory):
        return {'valid': False, 'errors': ['Элементы parts, steps и inventory должны быть объектами.'],
                'warnings': []}

    need(guide.get('units') == 'mm', 'Единицы сценария — миллиметры: units = "mm".')
    need(bool(parts) and bool(steps), 'Списки parts и steps не могут быть пустыми.')
    need(guide.get('total_steps') == len(steps), 'total_steps не совпадает с числом шагов.')

    ids = [p.get('id') for p in parts]
    need(all(isinstance(i, str) and i for i in ids), 'У каждой детали нужен строковый id.')
    if not all(isinstance(i, str) for i in ids):
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    need(len(set(ids)) == len(ids), 'id деталей повторяются.')
    id_set = set(ids)

    leaves = {}
    for p in parts:
        label = p['id']
        need(vector(p.get('position')), f'{label}: неверное положение position.')
        b = p.get('bounds')
        ok = isinstance(b, list) and len(b) == 2 and all(vector(v) for v in b)
        need(ok, f'{label}: bounds — два вектора из трёх конечных чисел.')
        if ok:
            need(all(b[0][i] <= b[1][i] for i in range(3)),
                 f'{label}: bounds перевёрнуты (минимум больше максимума).')
        for leaf in p.get('cad_leaves', []):
            if leaf in leaves:
                errors.append(f'{label}: экземпляр CAD уже отдан детали {leaves[leaf]}: {leaf}')
            leaves[leaf] = label

    keys = [p.get('key') for p in inventory]
    need(all(isinstance(k, str) and k for k in keys), 'Ключи комплекта inventory — непустые строки.')
    if not all(isinstance(k, str) for k in keys):
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    need(len(set(keys)) == len(keys), 'Ключи комплекта inventory повторяются.')
    key_set = set(keys)
    for row in inventory:
        need(quantity(row.get('qty')), f"Комплект {row.get('key')}: неверное количество qty.")

    used = set()
    for index, s in enumerate(steps, 1):
        need(s.get('step') == index, f'Номера шагов идут подряд: ожидался {index}.')
        camera = s.get('camera', {})
        need(isinstance(camera, dict) and vector(camera.get('pos')) and vector(camera.get('target')),
             f'Шаг {index}: неверная камера (нужны pos и target).')
        rows = s.get('required_parts', [])
        actions = s.get('actions', [])
        if not isinstance(rows, list) or not isinstance(actions, list):
            errors.append(f'Шаг {index}: required_parts и actions должны быть списками.')
            continue
        for row in rows:
            if not isinstance(row, dict):
                errors.append(f'Шаг {index}: неверная карточка детали.')
                continue
            need(row.get('key') in key_set, f'Шаг {index}: ключа {row.get("key")} нет в комплекте inventory.')
            need(quantity(row.get('qty')), f'Шаг {index}: неверное количество на карточке.')
        for a in actions:
            if not isinstance(a, dict):
                errors.append(f'Шаг {index}: неверное действие.')
                continue
            pid = a.get('part')
            need(isinstance(pid, str) and pid in id_set,
                 f'Шаг {index}: действие ссылается на неизвестную деталь {pid}.')
            if isinstance(pid, str):
                used.add(pid)
            need(vector(a.get('offset')), f'Шаг {index}, {pid}: неверный разнос offset.')
            axis = a.get('axis')
            need(vector(axis) and sum(x * x for x in axis) > 1e-15, f'Шаг {index}, {pid}: неверная ось axis.')
            need(number(a.get('spin', 0)), f'Шаг {index}, {pid}: неверный поворот spin.')
            if 'phase' in a:
                phase = a['phase']
                ok = isinstance(phase, list) and len(phase) == 2 and all(number(x) for x in phase)
                need(ok and 0 <= phase[0] < phase[1] <= 1,
                     f'Шаг {index}, {pid}: неверный интервал phase (нужно 0 <= начало < конец <= 1).')
                need(bool(s.get('custom_phases')), f'Шаг {index}: интервалы phase требуют custom_phases.')
            if 'show_after' in a:
                need(number(a['show_after']) and 0 <= a['show_after'] <= 1,
                     f'Шаг {index}, {pid}: неверный show_after (от 0 до 1).')
        for pid in s.get('isolated_parts', []):
            need(pid in id_set, f'Шаг {index}: неизвестная деталь {pid} в isolated_parts.')

    need(not (id_set - used), 'Детали не участвуют ни в одном шаге: ' + ', '.join(sorted(id_set - used)))

    questions = guide.get('open_questions', [])
    if questions:
        warnings.append(f'Открытых вопросов по фактам: {len(questions)}. '
                        'Порядок сборки и комплект требуют проверки.')
        status = str(guide.get('release_status', '')).lower()
        need(not any(x in status for x in ['approved', 'утвержден', 'утверждён']),
             'Нельзя утверждать выпуск при открытых вопросах.')

    return {'valid': not errors, 'parts': len(parts), 'steps': len(steps), 'inventory_types': len(inventory),
            'cad_occurrences': len(leaves), 'errors': errors, 'warnings': warnings}


def main():
    try:
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('scenario', type=Path, help='файл сценария .json')
    parser.add_argument('--output', type=Path, help='куда записать отчёт .json')
    args = parser.parse_args()
    try:
        report = validate(json.loads(args.scenario.read_text(encoding='utf-8-sig')))
    except (ValueError, OSError, TypeError, KeyError) as e:
        report = {'valid': False, 'errors': [str(e)], 'warnings': []}
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    print(encoded)
    if args.output:
        args.output.write_text(encoded + '\n', encoding='utf-8')
    return 0 if report['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
