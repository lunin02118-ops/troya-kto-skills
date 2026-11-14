"""Verified copy-first skill installation; no CAD calls or client cache cleanup.

The package may come from a SOLIDWORKS PDM vault view, where files are read-only: installed copies are made writable,
and staging folders are made writable before removal.
"""
from pathlib import Path
import hashlib
import os
import shutil
import stat
import uuid

IGNORED = {'__pycache__', '.git', '.pytest_cache', 'test_output'}


def reject_links(path):
    path = Path(path).absolute()
    for node in (path, *path.parents):
        try:
            st = node.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(st.st_mode) or getattr(st, 'st_file_attributes', 0) & 0x400:
            raise ValueError(f'Reparse point is not allowed: {node}')
    return path


def ignored(name):
    return name in IGNORED or name.endswith('.pyc') or name.startswith('~$')


def make_writable(root):
    """Clear the read-only attribute in a whole tree (copytree carries it over from a PDM view)."""
    root = Path(root)
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            _writable(Path(directory)/name)
    _writable(root)


def _writable(path):
    mode = path.lstat().st_mode
    if not mode & stat.S_IWRITE:
        os.chmod(path, mode | stat.S_IWRITE)


def remove_tree(path):
    """shutil.rmtree that does not fail on read-only files."""
    path = reject_links(path)
    make_writable(path)
    shutil.rmtree(path)


def manifest(root):
    root = reject_links(root)
    if not root.exists():
        return {}
    if not root.is_dir():
        raise ValueError(f'Not a directory: {root}')
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            reject_links(Path(directory)/name)
        dirs[:] = [n for n in dirs if not ignored(n)]
        for name in files:
            if not ignored(name):
                p = Path(directory)/name
                result[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def difference(source, target):
    left, right = manifest(source), manifest(target)
    return dict(added=sorted(left.keys()-right.keys()), removed=sorted(right.keys()-left.keys()),
                changed=sorted(k for k in left.keys() & right.keys() if left[k] != right[k]),
                source_files=len(left), target_files=len(right))


def differs(diff):
    return any(diff[k] for k in ('added', 'removed', 'changed'))


def synchronize(pairs, *, execute=False, conflict_policy='abort'):
    """Stage every package before commit; retain backups and rollback on failure.

    conflict_policy='source' explicitly chooses source versions, including removals.
    Planning is read-only; no directory is created until execute=True.
    """
    if conflict_policy not in ('abort', 'source'):
        raise ValueError('conflict_policy must be abort or source')
    plans = []
    for source, target in pairs:
        source, target = reject_links(source), reject_links(target)
        if source == target or source in target.parents or target in source.parents:
            raise ValueError('Source and target must be separate package directories')
        if not (source/'SKILL.md').is_file():
            raise ValueError(f'Missing SKILL.md: {source}')
        diff = difference(source, target)
        plans.append(dict(source=str(source), target=str(target), diff=diff,
                          source_manifest=manifest(source), target_manifest=manifest(target)))
    targets = [Path(p['target']) for p in plans]
    if len(set(targets)) != len(targets) or any(a in b.parents for a in targets for b in targets if a != b):
        raise ValueError('Duplicate or overlapping targets')
    changes = [p for p in plans if differs(p['diff'])]
    if not execute:
        return dict(mode='plan', plans=plans)
    conflicts = [p['target'] for p in changes if p['target_manifest']]
    if conflicts and conflict_policy == 'abort':
        raise ValueError('Different installed content; choose --conflict-policy source: '+', '.join(conflicts))
    run = uuid.uuid4().hex
    staged, committed = [], []
    try:
        for plan in changes:
            src, dst = Path(plan['source']), Path(plan['target'])
            dst.parent.mkdir(parents=True, exist_ok=True)
            stage = dst.parent/f'.skill-stage-{run}-{dst.name}'
            backup = dst.parent/'.skill-sync-backups'/run/dst.name
            reject_links(backup)
            plan.update(stage=str(stage), backup=str(backup), had_target=dst.exists(), replaced=False)
            staged.append(plan)
            shutil.copytree(src, stage, ignore=lambda d,names:[n for n in names if ignored(n)])
            make_writable(stage)
            if manifest(stage) != plan['source_manifest'] or manifest(src) != plan['source_manifest']:
                raise RuntimeError(f'Source changed during staging: {src}')
        for plan in staged:
            reject_links(plan['target'])
            reject_links(plan['backup'])
            if manifest(plan['target']) != plan['target_manifest']:
                raise RuntimeError(f'Target changed during staging: {plan["target"]}')
        for plan in staged:
            dst, stage, backup = map(Path, (plan['target'],plan['stage'],plan['backup']))
            committed.append(plan)
            if plan['had_target']:
                backup.parent.mkdir(parents=True,exist_ok=True)
                dst.rename(backup)
                plan['replaced'] = True
            stage.rename(dst)
            plan['installed'] = True
            if manifest(dst) != plan['source_manifest']:
                raise RuntimeError(f'Installed SHA mismatch: {dst}')
        return dict(mode='executed', plans=plans, backups=[p['backup'] for p in staged if p['had_target']])
    except Exception as exc:
        failures=[]
        for plan in reversed(committed):
            dst, backup = Path(plan['target']), Path(plan['backup'])
            try:
                if plan.get('installed') and dst.exists():
                    dst.rename(dst.parent/f'.skill-failed-{run}-{dst.name}')
                if plan['replaced'] and backup.exists():
                    backup.rename(dst)
            except Exception as rollback_error:
                failures.append(str(rollback_error))
        if failures:
            raise RuntimeError(f'{exc}; rollback errors: {failures}; backups retained') from exc
        raise
    finally:
        for plan in staged:
            stage=Path(plan['stage'])
            if stage.exists():
                reject_links(stage)
                if stage.parent != Path(plan['target']).parent or not stage.name.startswith(f'.skill-stage-{run}-'):
                    raise RuntimeError('Invalid staging cleanup path')
                remove_tree(stage)
