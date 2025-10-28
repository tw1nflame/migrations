"""
Модуль оптимизации для планирования волн миграции
Реализует алгоритмы максимального покрытия и set cover
"""

import pandas as pd
import io
from typing import Dict, Set, List, Tuple
from collections import defaultdict
from data_processor import DataProcessor
from ILP import ILPSoftwareSelector


class MigrationOptimizer:
    """
    Класс для оптимизации планирования волн миграции
    """

    def __init__(self, processor: DataProcessor):
        """
        Инициализация оптимизатора

        Args:
            processor: Обработанные данные из DataProcessor
        """
        self.processor = processor

    def find_best_software_set(
        self,
        limit: int,
        already_tested: Set[str],
        remaining_arms: Set[str]
    ) -> Tuple[Set[str], Set[str]]:
        """
        Найти оптимальный набор ПО для тестирования в волне (ФИНАЛЬНАЯ ОПТИМИЗАЦИЯ).
        Использует инкрементальный эвристический алгоритм максимального покрытия.
        """
        wave_software = set()
        migrating_arms = set()
        available_software = set(self.processor.software_to_arms.keys()) - already_tested

        untested_needs: Dict[str, int] = {
            arm: len(self.processor.arm_software_map.get(arm, set()) - already_tested)
            for arm in remaining_arms
        }
        
        # Предрассчитываем популярность для случая, когда нет "закрывающих" ПО
        popularity = {
            sw: len(self.processor.software_to_arms.get(sw, set()) & remaining_arms)
            for sw in available_software
        }

        for _ in range(limit):
            if not available_software:
                break

            software_scores = defaultdict(int)
            
            # Строим карту {ПО: [АРМы, которые оно закроет]}
            # Это надежнее, чем вычислять `last_software_needed` внутри цикла
            last_sw_map = defaultdict(list)
            for arm, needs in untested_needs.items():
                if needs == 1:
                    # Вычисляем единственное недостающее ПО
                    # Используем next + iter для безопасного извлечения одного элемента
                    try:
                        last_sw = next(iter(self.processor.arm_software_map[arm] - already_tested - wave_software))
                        if last_sw in available_software:
                            last_sw_map[last_sw].append(arm)
                    except StopIteration:
                        # Это может произойти, если ПО уже было выбрано в wave_software
                        # на предыдущей итерации этого же цикла. Безопасно пропускаем.
                        pass
            
            # Считаем очки на основе построенной карты
            if last_sw_map:
                software_scores = {sw: len(arms) for sw, arms in last_sw_map.items()}

            best_software = None
            if software_scores:
                best_software = max(software_scores, key=software_scores.get)
            else:
                current_popularity = {sw: pop for sw, pop in popularity.items() if sw in available_software}
                if current_popularity:
                    best_software = max(current_popularity, key=current_popularity.get)
            
            if best_software is None:
                break

            wave_software.add(best_software)
            available_software.remove(best_software)
            
            # Обновляем `untested_needs` и `migrating_arms`
            for arm in self.processor.software_to_arms.get(best_software, set()):
                if arm in untested_needs:
                    untested_needs[arm] -= 1
                    if untested_needs[arm] == 0:
                        migrating_arms.add(arm)
                        del untested_needs[arm]

        return wave_software, migrating_arms

    def calculate_waves(self, wave_limits: List[int], use_ilp: bool = False) -> Dict:
        """
        Рассчитать распределение ПО по волнам (ручной режим)

        Args:
            wave_limits: Список лимитов ПО для каждой волны
            use_ilp: Использовать точный ILP алгоритм (True) или эвристический (False)

        Returns:
            Словарь с результатами расчёта
        """
        tested_software = set()
        migrated_arms = set()
        software_wave_map = {}

        waves_data = []

        remaining_arms = set(self.processor.arm_software_map.keys())

        for wave_num, limit in enumerate(wave_limits, 1):
            # Выбираем алгоритм оптимизации
            if use_ilp:
                ilp_solver = ILPSoftwareSelector(self.processor)
                wave_software, wave_arms = ilp_solver.find_best_software_set_ilp(
                    limit=limit,
                    already_tested=tested_software,
                    remaining_arms=remaining_arms - migrated_arms
                )
            else:
                wave_software, wave_arms = self.find_best_software_set(
                    limit=limit,
                    already_tested=tested_software,
                    remaining_arms=remaining_arms - migrated_arms
                )

            # Обновляем глобальные множества
            tested_software.update(wave_software)
            migrated_arms.update(wave_arms)
            remaining_arms -= wave_arms

            # Помечаем каждое ПО номером волны
            for software in wave_software:
                software_wave_map[software] = wave_num

            # Сохраняем статистику волны
            waves_data.append({
                'wave_number': wave_num,
                'software_selected': len(wave_software),
                'software_list': list(wave_software),
                'arms_migrated': len(wave_arms),
                'arms_list': list(wave_arms)
            })

        return {
            'waves': waves_data,
            'total_tested_software': len(tested_software),
            'total_migrated_arms': len(migrated_arms),
            'software_wave_map': software_wave_map,
            'tested_software': tested_software,
            'migrated_arms': migrated_arms
        }

    def find_minimum_software_for_coverage(
        self,
        target_arms_count: int,
        already_tested: Set[str] = None,
        use_ilp: bool = False
    ) -> Tuple[Set[str], Set[str]]:
        """
        Найти минимальный набор ПО для покрытия заданного количества АРМ.
        
        Args:
            target_arms_count: Целевое количество АРМ для покрытия
            already_tested: Уже протестированное ПО
            use_ilp: Использовать точный ILP алгоритм (True) или эвристический (False)
        
        Returns:
            Кортеж (выбранное ПО, покрытые АРМ)
        """
        if already_tested is None:
            already_tested = set()

        # Выбираем алгоритм
        if use_ilp:
            ilp_solver = ILPSoftwareSelector(self.processor)
            return ilp_solver.find_minimum_software_for_coverage_ilp(
                target_arms_count=target_arms_count,
                already_tested=already_tested
            )
        
        # Эвристический алгоритм
        selected_software = set()
        
        # Начинаем с уже покрытых АРМ, если они есть
        # Это будет нашей отправной точкой и целью для цикла
        covered_arms = self.processor.get_covered_arms(already_tested)
        available_software = set(self.processor.software_to_arms.keys()) - already_tested

        # Цикл продолжается, пока реальное число ПОЛНОСТЬЮ покрытых АРМ меньше цели
        while len(covered_arms) < target_arms_count and available_software:
            best_software = None
            best_new_coverage_count = -1
            
            # Ключевая оптимизация: работаем с множеством АРМ, которые еще НЕ покрыты
            uncovered_arms = set(self.processor.arm_software_map.keys()) - covered_arms

            # Если покрывать больше некого, выходим
            if not uncovered_arms:
                break

            # На каждом шаге выбираем ПО, которое "затрагивает" максимальное число
            # еще не покрытых АРМ. Это и есть правильная эвристика для Set Cover.
            for software in available_software:
                # Считаем, сколько новых АРМ "затронет" это ПО
                newly_covered_count = len(self.processor.software_to_arms.get(software, set()) & uncovered_arms)
                if newly_covered_count > best_new_coverage_count:
                    best_new_coverage_count = newly_covered_count
                    best_software = software

            # Если ни одно ПО не помогает покрыть оставшихся, выходим
            if best_software is None:
                break

            # Добавляем лучшее ПО в наш набор
            selected_software.add(best_software)
            available_software.remove(best_software)
            
            # После выбора ПО, мы должны ПЕРЕСЧИТАТЬ, сколько АРМ теперь ПОЛНОСТЬЮ покрыты.
            # Это медленная операция, но она необходима для корректной работы условия `while`.
            # Для скорости можно было бы использовать эвристику, но для точности лучше так.
            covered_arms = self.processor.get_covered_arms(
                already_tested | selected_software
            )

        return selected_software, covered_arms

    def calculate_auto_recommendations(self) -> Dict:
        """
        Рассчитать автоматические рекомендации для первых двух волн

        Returns:
            Словарь с рекомендациями
        """
        total_arms = self.processor.total_arms

        # Волна 1: Минимальный набор (20% АРМ)
        target_20_percent = int(total_arms * 0.2)
        wave1_min_software, wave1_min_arms = self.find_minimum_software_for_coverage(
            target_arms_count=target_20_percent
        )

        # Волна 1: Оптимальный набор (100 ПО)
        wave1_opt_software, wave1_opt_arms = self.find_best_software_set(
            limit=min(100, self.processor.total_software),
            already_tested=set(),
            remaining_arms=set(self.processor.arm_software_map.keys())
        )

        # Волна 2: Оптимальный набор (100 ПО после волны 1)
        remaining_arms_after_wave1 = (
            set(self.processor.arm_software_map.keys()) - wave1_opt_arms
        )
        wave2_opt_software, wave2_opt_arms = self.find_best_software_set(
            limit=min(100, self.processor.total_software),
            already_tested=wave1_opt_software,
            remaining_arms=remaining_arms_after_wave1
        )

        return {
            'wave1_min': {
                'software_count': len(wave1_min_software),
                'arms_count': len(wave1_min_arms),
                'software_list': list(wave1_min_software),
                'arms_list': list(wave1_min_arms)
            },
            'wave1_opt': {
                'software_count': len(wave1_opt_software),
                'arms_count': len(wave1_opt_arms),
                'software_list': list(wave1_opt_software),
                'arms_list': list(wave1_opt_arms)
            },
            'wave2_opt': {
                'software_count': len(wave2_opt_software),
                'arms_count': len(wave2_opt_arms),
                'software_list': list(wave2_opt_software),
                'arms_list': list(wave2_opt_arms)
            }
        }

    def export_to_excel(self, results: Dict, original_filename: str) -> io.BytesIO:
        """
        Экспортировать результаты в Excel файл с тремя листами

        Args:
            results: Результаты расчёта волн
            original_filename: Имя исходного файла

        Returns:
            BytesIO буфер с Excel файлом
        """
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист 1: "Data" - исходные данные + столбец "Волна миграции"
            df_data = self.processor.original_df.copy()

            # Добавляем столбец с номером волны
            software_wave_map = results['software_wave_map']

            def get_wave(software_name):
                return software_wave_map.get(software_name, 'N/A')

            df_data['Волна миграции'] = df_data[
                self.processor.software_column
            ].apply(get_wave)

            df_data.to_excel(writer, sheet_name='Data', index=False)

            # Лист 2: "Статистика по волнам"
            wave_stats = []
            cumulative_arms = 0
            cumulative_software = 0

            for wave_data in results['waves']:
                wave_num = wave_data['wave_number']
                software_count = wave_data['software_selected']
                arms_count = wave_data['arms_migrated']

                cumulative_arms += arms_count
                cumulative_software += software_count

                wave_stats.append({
                    'Волна': f"Волна {wave_num}",
                    'Лимит ПО': software_count,  # В результатах уже ограничено лимитом
                    'Выбрано ПО': software_count,
                    'АРМ в волне': arms_count,
                    'АРМ накопительно': cumulative_arms
                })

            # Итоговая строка
            wave_stats.append({
                'Волна': 'ИТОГО',
                'Лимит ПО': cumulative_software,
                'Выбрано ПО': cumulative_software,
                'АРМ в волне': '',
                'АРМ накопительно': cumulative_arms
            })

            df_waves = pd.DataFrame(wave_stats)
            df_waves.to_excel(writer, sheet_name='Статистика по волнам', index=False)

            # Лист 3: "Общая статистика"
            general_stats = {
                'Метрика': [
                    'Всего АРМ/пользователей',
                    'Всего уникального ПО',
                    'Всего уникальных наборов ПО',
                    'Всего АРМ, покрытых планом',
                    'Всего ПО, включенного в план',
                    'Процент покрытия АРМ',
                    'Процент использования ПО'
                ],
                'Значение': [
                    self.processor.total_arms,
                    self.processor.total_software,
                    len(self.processor.set_to_arms_map),
                    results['total_migrated_arms'],
                    results['total_tested_software'],
                    f"{(results['total_migrated_arms'] / self.processor.total_arms * 100):.1f}%",
                    f"{(results['total_tested_software'] / self.processor.total_software * 100):.1f}%"
                ]
            }

            df_general = pd.DataFrame(general_stats)
            df_general.to_excel(writer, sheet_name='Общая статистика', index=False)

        output.seek(0)
        return output


