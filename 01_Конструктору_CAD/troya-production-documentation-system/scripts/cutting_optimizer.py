#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль 1D-раскроя металлопроката ТОО «Компания TROYA».
Оптимизирует раскрой стандартных 6-метровых хлыстов с учетом:
- Длины хлыста (по умолчанию 6000 мм)
- Ширины реза / пропила (керф, по умолчанию 4.0 мм)
- Торцовки краев хлыста (по умолчанию 20.0 мм: 10 мм с каждой стороны)
- Порога делового обрезка (по умолчанию >= 500 мм)
- Расчета коэффициента использования металла (КИМ)
"""

import sys
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple


@dataclass
class CutPiece:
    id: str
    name: str
    length: float
    qty: int
    material: str
    weight_per_m: float = 0.0


@dataclass
class MaterialStockResult:
    material: str
    standard_bar_length: float
    kerf: float
    trim: float
    weight_per_m: float
    total_parts_count: int
    net_length_m: float
    net_weight_kg: float
    bars_count: int
    gross_length_m: float
    gross_weight_kg: float
    usable_remnants: List[Dict[str, Any]]
    total_usable_remnant_m: float
    total_usable_remnant_kg: float
    scrap_length_m: float
    scrap_weight_kg: float
    kim_percent: float
    kim_effective_percent: float
    patterns: List[Dict[str, Any]]


class CuttingOptimizer:
    def __init__(
        self,
        bar_length: float = 6000.0,
        kerf: float = 4.0,
        trim: float = 20.0,
        usable_remnant_threshold: float = 500.0,
        cnc_chuck_tail: float = 200.0,
        is_cnc_tube: bool = True,
    ):
        self.bar_length = bar_length
        self.kerf = kerf
        self.trim = trim
        self.usable_remnant_threshold = usable_remnant_threshold
        self.cnc_chuck_tail = cnc_chuck_tail if is_cnc_tube else 0.0
        self.effective_bar_length = bar_length - trim - self.cnc_chuck_tail

    def _generate_patterns(self, lengths: List[float]) -> List[List[int]]:
        n = len(lengths)
        patterns = []

        def gen(idx, current_pat, current_len):
            if idx == n:
                if sum(current_pat) > 0:
                    patterns.append(list(current_pat))
                return
            c = 0
            while True:
                add = c * lengths[idx] + (c * self.kerf if current_len > 0 else max(0, (c - 1) * self.kerf))
                tot = current_len + (add if current_len > 0 else (c * lengths[idx] + max(0, (c - 1) * self.kerf)))
                if tot > self.effective_bar_length:
                    break
                c += 1
            for count in range(c - 1, -1, -1):
                if count == 0:
                    gen(idx + 1, current_pat + [0], current_len)
                else:
                    add = count * lengths[idx] + (count * self.kerf if current_len > 0 else (count - 1) * self.kerf)
                    gen(idx + 1, current_pat + [count], current_len + add)

        gen(0, [], 0)
        return patterns

    def _solve_patterns(self, lengths: List[float], demands: List[int]) -> List[Tuple[List[int], int]]:
        patterns = self._generate_patterns(lengths)
        n = len(lengths)

        # Вычисляем остаток каждого паттерна
        def pat_remnant(pat):
            tot_len = sum(pat[i] * lengths[i] for i in range(n))
            cuts = max(0, sum(pat) - 1)
            return self.effective_bar_length - (tot_len + cuts * self.kerf)

        # Сортируем: сначала с минимальным остатком
        patterns.sort(key=lambda p: pat_remnant(p))

        # Ограниченный поиск с возвратом (greedy + local improvement)
        best_sol = None
        best_bars = sum(demands)  # худшая оценка

        # Жадное начальное решение по паттернам
        cur_demands = list(demands)
        sol = []
        tot_b = 0
        for pat in patterns:
            # сколько раз можно применить паттерн
            possible = []
            for i in range(n):
                if pat[i] > 0:
                    possible.append(cur_demands[i] // pat[i])
            if possible:
                k = min(possible)
                if k > 0:
                    sol.append((pat, k))
                    tot_b += k
                    for i in range(n):
                        cur_demands[i] -= k * pat[i]

        # Добиваем остаток жадно
        for i in range(n):
            while cur_demands[i] > 0:
                # ищем наилучший паттерн для покрытия
                best_p = None
                best_cov = 0
                for p in patterns:
                    cov = min(cur_demands[i], p[i])
                    if cov > best_cov:
                        best_cov = cov
                        best_p = p
                if best_p:
                    sol.append((best_p, 1))
                    tot_b += 1
                    for j in range(n):
                        cur_demands[j] -= best_p[j]
                else:
                    break

        # Сворачиваем одинаковые паттерны
        final_dict = {}
        for p, k in sol:
            pk = tuple(p)
            final_dict[pk] = final_dict.get(pk, 0) + k

        return [(list(p), k) for p, k in final_dict.items() if k > 0]

    def optimize_profile(
        self,
        material: str,
        pieces: List[CutPiece],
        weight_per_m: float = 0.0
    ) -> MaterialStockResult:
        total_parts = sum(p.qty for p in pieces)
        net_len_mm = sum(p.length * p.qty for p in pieces)

        if not pieces or total_parts == 0:
            return MaterialStockResult(
                material=material,
                standard_bar_length=self.bar_length,
                kerf=self.kerf,
                trim=self.trim,
                weight_per_m=weight_per_m,
                total_parts_count=0,
                net_length_m=0.0,
                net_weight_kg=0.0,
                bars_count=0,
                gross_length_m=0.0,
                gross_weight_kg=0.0,
                usable_remnants=[],
                total_usable_remnant_m=0.0,
                total_usable_remnant_kg=0.0,
                scrap_length_m=0.0,
                scrap_weight_kg=0.0,
                kim_percent=0.0,
                kim_effective_percent=0.0,
                patterns=[]
            )

        # Сортируем типы по убыванию длины
        unique_pieces = sorted(pieces, key=lambda p: p.length, reverse=True)
        lengths = [p.length for p in unique_pieces]
        demands = [p.qty for p in unique_pieces]

        # Решаем оптимизационную задачу
        pattern_solution = self._solve_patterns(lengths, demands)

        packed_patterns = []
        bars_count = 0

        for pat_counts, k in pattern_solution:
            bars_count += k
            pat_pieces = []
            for idx, cnt in enumerate(pat_counts):
                for _ in range(cnt):
                    pat_pieces.append(lengths[idx])
            used_len = sum(pat_pieces) + max(0, len(pat_pieces) - 1) * self.kerf
            remnant = round(self.bar_length - self.trim - used_len, 2)
            is_usable = remnant >= self.usable_remnant_threshold

            packed_patterns.append({
                "lengths": pat_pieces,
                "used_length": round(used_len, 2),
                "remnant": remnant,
                "is_usable": is_usable,
                "count": k
            })

        packed_patterns.sort(key=lambda x: x["count"], reverse=True)

        net_length_m = round(net_len_mm / 1000.0, 3)
        net_weight_kg = round(net_length_m * weight_per_m, 2)
        gross_length_m = round(bars_count * self.bar_length / 1000.0, 3)
        gross_weight_kg = round(gross_length_m * weight_per_m, 2)

        usable_remnants = []
        total_usable_m = 0.0

        for pat in packed_patterns:
            if pat["is_usable"]:
                m = round(pat["remnant"] * pat["count"] / 1000.0, 3)
                kg = round(m * weight_per_m, 2)
                usable_remnants.append({
                    "length_mm": pat["remnant"],
                    "count": pat["count"],
                    "total_m": m,
                    "total_kg": kg
                })
                total_usable_m += m

        total_scrap_m = round(gross_length_m - net_length_m - total_usable_m, 3)
        total_scrap_kg = round(total_scrap_m * weight_per_m, 2)
        total_usable_kg = round(total_usable_m * weight_per_m, 2)

        kim_percent = round((net_length_m / gross_length_m) * 100.0, 2) if gross_length_m > 0 else 0.0
        kim_effective_percent = round(((net_length_m + total_usable_m) / gross_length_m) * 100.0, 2) if gross_length_m > 0 else 0.0

        return MaterialStockResult(
            material=material,
            standard_bar_length=self.bar_length,
            kerf=self.kerf,
            trim=self.trim,
            weight_per_m=weight_per_m,
            total_parts_count=total_parts,
            net_length_m=net_length_m,
            net_weight_kg=net_weight_kg,
            bars_count=bars_count,
            gross_length_m=gross_length_m,
            gross_weight_kg=gross_weight_kg,
            usable_remnants=usable_remnants,
            total_usable_remnant_m=round(total_usable_m, 3),
            total_usable_remnant_kg=round(total_usable_kg, 2),
            scrap_length_m=round(total_scrap_m, 3),
            scrap_weight_kg=round(total_scrap_kg, 2),
            kim_percent=kim_percent,
            kim_effective_percent=kim_effective_percent,
            patterns=packed_patterns
        )
