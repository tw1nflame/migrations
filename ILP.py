from typing import Optional, Set, Tuple, Dict
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpBinary, PULP_CBC_CMD, LpMinimize, LpStatus, HiGHS_CMD
from collections import defaultdict
from data_processor import DataProcessor
from pulp import HiGHS

class ILPSoftwareSelector:
    """
    Решатель задачи выбора оптимального набора ПО через Integer Linear Programming.
    Гарантирует математически оптимальное решение задачи максимального покрытия.
    """

    def __init__(self, processor: DataProcessor):
        self.processor = processor

    def find_best_software_set_ilp(
        self,
        limit: int,
        already_tested: Set[str],
        remaining_arms: Set[str],
        selection_bonus: float = 0.001,
        time_limit: Optional[int] = None,
        warm_start_solution: Optional[Set[str]] = None
    ) -> Tuple[Set[str], Set[str]]:
        """
        Находит оптимальный набор ПО, максимизируя количество ПОЛНОСТЬЮ покрытых АРМов.
        
        Args:
            time_limit: Максимальное время работы решателя в секундах (None = без ограничения).
                       При ограничении времени решатель может вернуть неоптимальное, но допустимое решение.
            warm_start_solution: Опциональное стартовое решение (набор ПО) для ускорения ILP.
        """
        available_software = list(
            set(self.processor.software_to_arms.keys()) - already_tested
        )
        
        if not available_software or not remaining_arms:
            return set(), set()
        
        # Создаем задачу максимизации
        problem = LpProblem("Maximize_Migrating_ARMs", LpMaximize)
        
        # ПЕРЕМЕННЫЕ РЕШЕНИЯ
        # x[sw] = 1 если ПО `sw` выбрано, 0 иначе
        x = {
            sw: LpVariable(f"sw_{i}", cat=LpBinary)
            for i, sw in enumerate(available_software)
        }
        
        # Задаем начальные значения из warm start (если есть)
        if warm_start_solution:
            for sw in available_software:
                x[sw].setInitialValue(1 if sw in warm_start_solution else 0)
        
        # z[arm] = 1 если АРМ `arm` полностью покрыт, 0 иначе
        z = {
            arm: LpVariable(f"arm_{j}", cat=LpBinary)
            for j, arm in enumerate(remaining_arms)
        }
        
        # Задаем начальные значения для z[arm] на основе warm_start
        if warm_start_solution:
            for arm in remaining_arms:
                untested_sw_for_arm = self.processor.arm_software_map.get(arm, set()) - already_tested
                # АРМ покрыт, если все его непротестированное ПО есть в warm_start
                is_covered = untested_sw_for_arm and untested_sw_for_arm.issubset(warm_start_solution)
                z[arm].setInitialValue(1 if is_covered else 0)
        
        # Создаем индексы для уникальных имён ограничений
        arm_index = {arm: j for j, arm in enumerate(remaining_arms)}
        sw_index = {sw: i for i, sw in enumerate(available_software)}
        
        # ЦЕЛЕВАЯ ФУНКЦИЯ
        # Максимизируем количество полностью покрытых АРМов.
        # Добавляем маленький бонус за каждое выбранное ПО, чтобы решатель
        # стремился выбрать ПО до лимита, если это не ухудшает основной показатель.
        problem += lpSum(z.values()) + selection_bonus * lpSum(x.values()), "Objective"
        
        # ОГРАНИЧЕНИЯ
        
        # 1. Ограничение на количество выбранного ПО
        problem += lpSum(x.values()) <= limit, "Software_Limit"
        
        # 2. Связь между полным покрытием АРМа (z) и выбором ПО (x)
        for arm in remaining_arms:
            # Находим все ПО для этого АРМа, которое еще не протестировано
            untested_sw_for_arm = [
                sw for sw in (self.processor.arm_software_map.get(arm, set()) - already_tested)
                if sw in available_software
            ]
            
            # Если для АРМа нет необходимого ПО в доступном списке, он не может быть покрыт
            if not untested_sw_for_arm:
                problem += z[arm] == 0, f"ARM_uncoverable_a{arm_index[arm]}"
                continue

            # Чтобы АРМ был покрыт (z[arm] = 1), КАЖДОЕ из его непротестированных ПО должно быть выбрано.
            # Это логическое "И", которое в ILP моделируется так:
            # Ограничение "вниз": z[arm] должно быть <= x[sw] для каждого нужного ПО
            for sw in untested_sw_for_arm:
                problem += z[arm] <= x[sw], f"ARM_comp_a{arm_index[arm]}_s{sw_index[sw]}"
            
            # Ограничение "вверх": z[arm] должно стать 1, если все x[sw] равны 1
            # z[arm] >= sum(x[sw]) - (N-1), где N - количество нужного ПО
            problem += (
                z[arm] >= lpSum(x[sw] for sw in untested_sw_for_arm) - (len(untested_sw_for_arm) - 1),
                f"ARM_force_a{arm_index[arm]}"
            )

        # РЕШЕНИЕ ЗАДАЧИ
        # Используем HiGHS решатель с поддержкой warm start
        solver = HiGHS(
            msg=0,
            timeLimit=time_limit,
            warmStart=True  # Включаем использование начальных значений переменных
        )

        problem.solve(solver)
        
        # ПРОВЕРКА СТАТУСА И ИЗВЛЕЧЕНИЕ РЕЗУЛЬТАТА
        status = LpStatus[problem.status]
        
        # Извлекаем решение из переменных (если есть)
        selected_software = {
            sw for sw in available_software
            if x[sw].varValue is not None and x[sw].varValue > 0.5
        }
        
        migrating_arms = {
            arm for arm in remaining_arms
            if z[arm].varValue is not None and z[arm].varValue > 0.5
        }
        
        # Если решение оптимальное или найдено непустое feasible решение - возвращаем его
        if status == 'Optimal' or (selected_software and migrating_arms):
            return selected_software, migrating_arms
        
        # Если solver не вернул решение (timeout без feasible), используем warm_start как fallback
        # Это происходит когда: status = 'Not Solved' или 'Infeasible' или другой неуспешный статус
        if warm_start_solution:
            # Вычисляем покрытые АРМы для warm_start решения
            covered_arms = set()
            for arm in remaining_arms:
                untested_sw_for_arm = self.processor.arm_software_map.get(arm, set()) - already_tested
                # АРМ покрыт, если все его непротестированное ПО есть в warm_start
                if untested_sw_for_arm and untested_sw_for_arm.issubset(warm_start_solution):
                    covered_arms.add(arm)
            
            return warm_start_solution, covered_arms
        
        # Нет ни решения от solver'а, ни warm_start - возвращаем пустое решение
        return set(), set()
    
    def find_minimum_software_for_coverage_ilp(
    self,
    target_arms_count: int,
    already_tested: Set[str] = None,
    warm_start_solution: Optional[Set[str]] = None,
    time_limit: Optional[int] = None
) -> Tuple[Set[str], Set[str]]:
        """
        ILP-вариант задачи Set Cover с поддержкой "теплого старта" и фильтрацией недостижимых пользователей.

        Args:
            target_arms_count: Целевое количество АРМов для покрытия.
            already_tested: Множество уже протестированного ПО.
            warm_start_solution: Опциональное стартовое решение (набор ПО) для ускорения.
            time_limit: Максимальное время работы решателя в секундах (None = без ограничения).
                       При ограничении времени решатель может вернуть неоптимальное, но допустимое решение.
        """
        if already_tested is None:
            already_tested = set()

        # --- Доступное ПО и пользователи ---
        available_software_set = set(self.processor.software_to_arms.keys()) - already_tested
        available_software = list(available_software_set)
        all_arms = set(self.processor.arm_software_map.keys())

        if not available_software or not all_arms:
            return set(), set()

        # --- Если есть warm start, используем его размер как верхнюю границу K ---
        if warm_start_solution:
            upper_bound = len(warm_start_solution)
        else:
            upper_bound = None

        # --- Фильтрация пользователей, которые требуют > K ПО ---
        def arm_degree(arm: str) -> int:
            """Количество ПО, требуемых для покрытия данного пользователя (с учетом already_tested)."""
            return len((self.processor.arm_software_map.get(arm, set()) - already_tested) & available_software_set)

        if upper_bound is not None:
            remaining_arms = {
                arm for arm in all_arms
                if 0 < arm_degree(arm) <= upper_bound
            }
        else:
            remaining_arms = {
                arm for arm in all_arms
                if arm_degree(arm) > 0
            }


        # --- Создаем задачу ILP ---
        problem = LpProblem("Minimize_Software_for_Target_Coverage", LpMinimize)

        # Переменные выбора ПО
        x = {sw: LpVariable(f"sw_{i}", cat=LpBinary) for i, sw in enumerate(available_software)}

        # Задаем начальные значения из warm start
        if warm_start_solution:
            for sw in available_software:
                x[sw].setInitialValue(1 if sw in warm_start_solution else 0)

        # Переменные покрытия пользователей
        z = {arm: LpVariable(f"arm_{j}", cat=LpBinary) for j, arm in enumerate(remaining_arms)}

        # Задаем начальные значения для z[arm] на основе warm_start
        if warm_start_solution:
            for arm in remaining_arms:
                untested_sw_for_arm = (self.processor.arm_software_map.get(arm, set()) - already_tested) & available_software_set
                # АРМ покрыт, если все его непротестированное ПО есть в warm_start
                is_covered = untested_sw_for_arm and untested_sw_for_arm.issubset(warm_start_solution)
                z[arm].setInitialValue(1 if is_covered else 0)

        # Создаем индексы для уникальных имён ограничений
        arm_index = {arm: j for j, arm in enumerate(remaining_arms)}
        sw_index = {sw: i for i, sw in enumerate(available_software)}

        # Целевая функция — минимизировать количество выбранных ПО
        problem += lpSum(x.values()), "Minimize_Software_Count"

        # --- Ограничения покрытия ---
        for arm in remaining_arms:
            untested_sw_for_arm = list(
                (self.processor.arm_software_map.get(arm, set()) - already_tested) & available_software_set
            )
            if not untested_sw_for_arm:
                problem += z[arm] == 0, f"MIN_uncoverable_a{arm_index[arm]}"
                continue

            n = len(untested_sw_for_arm)

            # z[arm] ≤ x[sw] для всех sw ∈ требуемом множестве
            for sw in untested_sw_for_arm:
                problem += z[arm] <= x[sw], f"MIN_comp_a{arm_index[arm]}_s{sw_index[sw]}"

            # z[arm] ≥ sum(x[sw]) - (n - 1)
            problem += z[arm] >= lpSum(x[sw] for sw in untested_sw_for_arm) - (n - 1), f"MIN_force_a{arm_index[arm]}"

        # Целевое количество покрытых пользователей
        problem += lpSum(z.values()) >= target_arms_count, "Target_Coverage"

        # --- Ограничение на количество ПО из warm start ---
        if warm_start_solution:
            problem += lpSum(x.values()) <= upper_bound, "Heuristic_Upper_Bound"

        # --- Решатель ---
        solver = HiGHS(
            timeLimit=time_limit,
            options=['randomSeed 123', 'randomCbcSeed 456'],
            msg=0,
            warmStart=True  # Включаем использование начальных значений переменных
        )
        problem.solve(solver)

        # --- Проверка статуса решения ---
        status = LpStatus[problem.status]
        
        # Извлекаем решение из переменных (если есть)
        selected_software = {sw for sw in available_software if x[sw].varValue is not None and x[sw].varValue > 0.5}
        covered_arms = {arm for arm in remaining_arms if z[arm].varValue is not None and z[arm].varValue > 0.5}
        
        # Если решение оптимальное или найдено непустое feasible решение - возвращаем его
        if status == 'Optimal' or (selected_software and covered_arms):
            return selected_software, covered_arms
        
        # Если solver не вернул решение, используем warm_start как fallback
        if warm_start_solution:
            covered_by_greedy = self.processor.get_covered_arms(already_tested | warm_start_solution)
            if len(covered_by_greedy) >= target_arms_count:
                return warm_start_solution, covered_by_greedy
        
        # Нет ни решения от solver'а, ни подходящего warm_start
        return set(), set()