"""
Модуль оптимизации для планирования волн миграции
Реализует алгоритмы максимального покрытия и set cover
"""

import pandas as pd
import io
from typing import Dict, Set, List, Tuple, Optional
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
                # Сортируем по очкам (по убыванию), затем по имени (по возрастанию)
                best_software = max(software_scores.keys(), key=lambda sw: (software_scores[sw], sw))
            else:
                current_popularity = {sw: pop for sw, pop in popularity.items() if sw in available_software}
                if current_popularity:
                    # То же самое для популярности
                    best_software = max(current_popularity.keys(), key=lambda sw: (current_popularity[sw], sw))
            
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

    def calculate_waves(self, wave_limits: List[int], use_ilp: bool = False, time_limit: Optional[int] = None) -> Dict:
        """
        Рассчитать распределение ПО по волнам (ручной режим)

        Args:
            wave_limits: Список лимитов ПО для каждой волны
            use_ilp: Использовать точный ILP алгоритм (True) или эвристический (False)
            time_limit: Максимальное время работы ILP решателя в секундах (только для use_ilp=True)

        Returns:
            Словарь с результатами расчёта
        """
        tested_software = set()
        migrated_arms = set()
        software_wave_map = {}
        arm_wave_map = {}  # Карта АРМ -> номер волны
        n_waves = len(wave_limits)
        waves_data = []

        remaining_arms = set(self.processor.arm_software_map.keys())

        for wave_num, limit in enumerate(wave_limits, 1):
            # Выбираем алгоритм оптимизации
            if use_ilp:
                ilp_solver = ILPSoftwareSelector(self.processor)
                wave_software, wave_arms = ilp_solver.find_best_software_set_ilp(
                    limit=limit,
                    already_tested=tested_software,
                    remaining_arms=remaining_arms - migrated_arms,
                    time_limit=time_limit / n_waves
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
            
            # Помечаем каждый мигрирующий АРМ номером волны
            for arm in wave_arms:
                arm_wave_map[arm] = wave_num

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
            'arm_wave_map': arm_wave_map,  # Добавляем карту АРМ -> волна
            'tested_software': tested_software,
            'migrated_arms': migrated_arms
        }

    def _find_minimum_software_greedy(
    self,
    target_arms_count: int,
    already_tested: Set[str]
) -> Tuple[Set[str], Set[str]]:
        """
        Эвристический (жадный) алгоритм для задачи Set Cover.
        Вынесен в отдельный метод для переиспользования.
        """
        selected_software = set()
        covered_arms = self.processor.get_covered_arms(already_tested)
        
        # Преобразуем в отсортированный список для детерминизма
        available_software_list = sorted(list(set(self.processor.software_to_arms.keys()) - already_tested))

        while len(covered_arms) < target_arms_count and available_software_list:
            uncovered_arms = set(self.processor.arm_software_map.keys()) - covered_arms
            if not uncovered_arms:
                break

            best_software = None
            best_score = -1
            
            # <<< ИЗМЕНЕНИЕ: Детерминированный выбор >>>
            for software in available_software_list:
                # Эвристика: выбираем ПО, которое затрагивает максимум еще не покрытых АРМ
                score = len(self.processor.software_to_arms.get(software, set()) & uncovered_arms)
                
                if score > best_score:
                    best_score = score
                    best_software = software
            # При равенстве очков будет выбрано ПО, которое идет раньше в отсортированном списке `available_software_list`
            
            if best_software is None:
                break

            selected_software.add(best_software)
            available_software_list.remove(best_software)
            
            # Пересчитываем полное покрытие после добавления ПО
            covered_arms = self.processor.get_covered_arms(already_tested | selected_software)

        return selected_software, covered_arms
    
    def find_minimum_software_for_coverage(
        self,
        target_arms_count: int,
        already_tested: Set[str] = None,
        use_ilp: bool = False,
        use_warm_start: bool = True,
        time_limit: Optional[int] = None
    ) -> Tuple[Set[str], Set[str]]:
        """
        Найти минимальный набор ПО для покрытия заданного количества АРМ.
        
        Args:
            time_limit: Максимальное время работы ILP решателя в секундах (только для use_ilp=True)
        """
        if already_tested is None:
            already_tested = set()

        if use_ilp:
            ilp_solver = ILPSoftwareSelector(self.processor)
            warm_start_solution = None

            # <<< ИЗМЕНЕНИЕ: Логика "теплого старта" >>>
            if use_warm_start:
                print("Calculating greedy solution for warm start...")
                greedy_solution, greedy_covered = self._find_minimum_software_greedy(
                    target_arms_count=target_arms_count,
                    already_tested=already_tested
                )
                # Убедимся, что жадный алгоритм вообще нашел решение
                if len(greedy_covered) >= target_arms_count:
                    print(f"Greedy solution found: {len(greedy_solution)} software. Using as warm start.")
                    warm_start_solution = greedy_solution
                else:
                    print("Greedy algorithm could not find a feasible solution. Running ILP without warm start.")
            
            return ilp_solver.find_minimum_software_for_coverage_ilp(
                target_arms_count=target_arms_count,
                already_tested=already_tested,
                warm_start_solution=warm_start_solution,  # Передаем полное решение (или None)
                time_limit=time_limit
            )
        else:
            # Если ILP не используется, просто вызываем жадный алгоритм
            return self._find_minimum_software_greedy(
                target_arms_count=target_arms_count,
                already_tested=already_tested
            )

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

    def export_to_excel(self, results: Dict, original_filename: str, tested_software_set: Set[str] = None) -> io.BytesIO:
        """
        Экспортировать результаты в Excel файл с тремя листами

        Args:
            results: Результаты расчёта волн
            original_filename: Имя исходного файла
            tested_software_set: Множество протестированного ПО (опционально)

        Returns:
            BytesIO буфер с Excel файлом
        """
        if tested_software_set is None:
            tested_software_set = set()
            
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист 1: "Data" - исходные данные + столбцы "Волна миграции" и опционально "ПО протестировано"
            df_data = self.processor.original_df.copy()

            # Добавляем столбец с номером волны на основе АРМа (не ПО!)
            arm_wave_map = results.get('arm_wave_map', {})

            def get_wave(arm_name):
                return arm_wave_map.get(arm_name, 'N/A')

            df_data['Волна миграции'] = df_data[
                self.processor.arm_column  # Используем столбец с АРМ, а не ПО
            ].apply(get_wave)
            
            # Добавляем столбец "ПО протестировано" только если есть протестированное ПО
            if tested_software_set:
                df_data['ПО протестировано'] = df_data[
                    self.processor.software_column
                ].apply(lambda sw: sw in tested_software_set)

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

    @staticmethod
    def create_software_export(software_list: List[str], tested_software_set: Set[str], sheet_name: str = 'ПО') -> io.BytesIO:
        """
        Создать Excel файл со списком ПО и столбцом "ПО протестировано"
        
        Args:
            software_list: Список ПО для экспорта
            tested_software_set: Множество протестированного ПО
            sheet_name: Название листа в Excel
            
        Returns:
            BytesIO буфер с Excel файлом
        """
        sorted_list = sorted(software_list)
        
        # Добавляем столбец "ПО протестировано" только если есть протестированное ПО
        if tested_software_set:
            df_software = pd.DataFrame({
                'ПО для тестирования': sorted_list,
                'ПО протестировано': [sw in tested_software_set for sw in sorted_list]
            })
        else:
            df_software = pd.DataFrame({
                'ПО для тестирования': sorted_list
            })
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_software.to_excel(writer, sheet_name=sheet_name, index=False)
        output.seek(0)
        return output
    
    @staticmethod
    def create_arms_export(arms_list: List[str], sheet_name: str = 'АРМ') -> io.BytesIO:
        """
        Создать Excel файл со списком АРМов
        
        Args:
            arms_list: Список АРМов для экспорта
            sheet_name: Название листа в Excel
            
        Returns:
            BytesIO буфер с Excel файлом
        """
        df_arms = pd.DataFrame({
            'Мигрирующие АРМ': sorted(arms_list)
        })
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_arms.to_excel(writer, sheet_name=sheet_name, index=False)
        output.seek(0)
        return output



