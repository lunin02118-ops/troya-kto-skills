"""Быстрая проверка validate_scenario.py: годный сценарий и четыре независимые ошибки.

Запуск: python test_validator.py
Если в навыке есть образец парты NOMAD V (examples/nomad_v_desk/assembly_guide.json),
проверяется и он.
"""
import json
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_scenario import validate  # noqa: E402

try:
    sys.stdout.reconfigure(errors='replace')
except (AttributeError, ValueError):
    pass

base = {
    'units': 'mm', 'total_steps': 1,
    'parts': [{'id': 'P1', 'position': [0, 0, 0], 'bounds': [[0, 0, 0], [1, 1, 1]], 'cad_leaves': ['part-1']}],
    'inventory': [{'key': 'screw', 'qty': 1}],
    'steps': [{'step': 1, 'camera': {'pos': [4, 5, 6], 'target': [0, 0, 0]},
               'required_parts': [{'key': 'screw', 'qty': 1}],
               'actions': [{'part': 'P1', 'offset': [0, 0, 10], 'axis': [0, 0, 1], 'spin': 360}]}],
    'release_status': 'review', 'open_questions': [],
}
assert validate(base)['valid'], validate(base)['errors']

unknown = deepcopy(base)
unknown['steps'][0]['actions'][0]['part'] = 'missing'
assert not validate(unknown)['valid']

phase = deepcopy(base)
phase['steps'][0]['actions'][0]['phase'] = [.8, .4]
phase['steps'][0]['custom_phases'] = True
assert not validate(phase)['valid']

bounds = deepcopy(base)
bounds['parts'][0]['bounds'][0][1] = 2
assert not validate(bounds)['valid']

approval = deepcopy(base)
approval['open_questions'] = ['package count']
approval['release_status'] = 'approved'
assert not validate(approval)['valid']

print('Проверка сценария: годный сценарий принят, четыре ошибки пойманы.')

sample = HERE.parent / 'examples' / 'nomad_v_desk' / 'assembly_guide.json'
if sample.is_file():
    report = validate(json.loads(sample.read_text(encoding='utf-8-sig')))
    assert report['valid'], report['errors']
    print(f"Образец парты NOMAD V годен: деталей {report['parts']}, шагов {report['steps']}, "
          f"позиций комплекта {report['inventory_types']}, экземпляров CAD {report['cad_occurrences']}, "
          f"предупреждений {len(report['warnings'])}.")
