"""
Модуль обработки данных для оптимизатора миграции
Преобразует сырые данные из Excel/CSV в структуры для оптимизации
"""

import pandas as pd
from typing import Dict, Set, FrozenSet
from collections import defaultdict


class DataProcessor:
    """
    Класс для обработки и подготовки данных о ПО на рабочих станциях
    """

    def __init__(self, df: pd.DataFrame, arm_column: str, software_column: str):
        """
        Инициализация процессора данных

        Args:
            df: DataFrame с исходными данными
            arm_column: Название столбца с идентификаторами АРМ
            software_column: Название столбца с наименованиями ПО
        """
        self.df = df.copy()
        self.arm_column = arm_column
        self.software_column = software_column

        # Основные структуры данных
        self.arm_software_map: Dict[str, Set[str]] = {}
        self.set_to_arms_map: Dict[FrozenSet[str], Set[str]] = {}
        self.software_to_arms: Dict[str, Set[str]] = defaultdict(set)

        # Статистика
        self.total_arms = 0
        self.total_software = 0
        self.original_df = None

    def process(self):
        """
        Основной метод обработки данных
        Выполняет все этапы преобразования
        """
        # Сохраняем оригинальный DataFrame
        self.original_df = self.df.copy()

        # Шаг 1: Очистка данных
        self._clean_data()

        # Шаг 2: Удаление дубликатов
        self._deduplicate()

        # Шаг 3: Создание основной карты АРМ -> ПО
        self._build_arm_software_map()

        # Шаг 4: Создание инвертированной карты наборов ПО -> АРМ
        self._build_set_to_arms_map()

        # Шаг 5: Создание карты ПО -> АРМ
        self._build_software_to_arms_map()

        # Шаг 6: Подсчёт статистики
        self._calculate_statistics()

    def _clean_data(self):
        """
        Очистка данных от пустых значений и пробелов
        """
        # Удаляем строки с пустыми значениями в ключевых столбцах
        self.df = self.df.dropna(subset=[self.arm_column, self.software_column])

        # Убираем лишние пробелы
        self.df[self.arm_column] = self.df[self.arm_column].astype(str).str.strip()
        self.df[self.software_column] = self.df[self.software_column].astype(str).str.strip()

        # Удаляем пустые строки после очистки
        self.df = self.df[
            (self.df[self.arm_column] != '') &
            (self.df[self.software_column] != '')
        ]

    def _deduplicate(self):
        """
        Удаление дубликатов пар (АРМ, ПО)
        """
        # Оставляем только уникальные пары
        self.df = self.df.drop_duplicates(
            subset=[self.arm_column, self.software_column]
        )

    def _build_arm_software_map(self):
        self.arm_software_map = self.df.groupby(self.arm_column)[self.software_column].apply(set).to_dict()

    def _build_set_to_arms_map(self):
        s = pd.Series(self.arm_software_map)
        self.set_to_arms_map = s.index.to_series().groupby(s.apply(frozenset)).apply(set).to_dict()

    def _build_software_to_arms_map(self):
        self.software_to_arms = self.df.groupby(self.software_column)[self.arm_column].apply(set).to_dict()

    def _calculate_statistics(self):
        """
        Подсчёт статистики по данным
        """
        self.total_arms = len(self.arm_software_map)
        self.total_software = len(self.software_to_arms)

    def get_software_popularity(self) -> Dict[str, int]:
        """
        Получить популярность каждого ПО (на скольких АРМ установлено)

        Returns:
            Словарь {ПО: количество АРМ}
        """
        return {
            software: len(arms)
            for software, arms in self.software_to_arms.items()
        }

    def get_arm_software_count(self) -> Dict[str, int]:
        """
        Получить количество ПО на каждом АРМ

        Returns:
            Словарь {АРМ: количество ПО}
        """
        return {
            arm: len(software_set)
            for arm, software_set in self.arm_software_map.items()
        }

    def get_set_statistics(self) -> Dict[str, any]:
        """
        Получить статистику по уникальным наборам ПО

        Returns:
            Словарь со статистикой
        """
        set_sizes = [len(s) for s in self.set_to_arms_map.keys()]
        set_arm_counts = [len(arms) for arms in self.set_to_arms_map.values()]

        return {
            'unique_sets': len(self.set_to_arms_map),
            'min_set_size': min(set_sizes) if set_sizes else 0,
            'max_set_size': max(set_sizes) if set_sizes else 0,
            'avg_set_size': sum(set_sizes) / len(set_sizes) if set_sizes else 0,
            'min_arms_per_set': min(set_arm_counts) if set_arm_counts else 0,
            'max_arms_per_set': max(set_arm_counts) if set_arm_counts else 0,
        }

    def get_arms_by_software_set(self, software_set: Set[str]) -> Set[str]:
        """
        Получить список АРМ, у которых установлен данный набор ПО

        Args:
            software_set: Множество ПО

        Returns:
            Множество идентификаторов АРМ
        """
        frozen_set = frozenset(software_set)
        return self.set_to_arms_map.get(frozen_set, set())

    def is_arm_covered(self, arm: str, tested_software: Set[str]) -> bool:
        """
        Проверить, покрыт ли АРМ протестированным ПО
        (все его программы протестированы)

        Args:
            arm: Идентификатор АРМ
            tested_software: Множество протестированного ПО

        Returns:
            True если все ПО на АРМ протестировано
        """
        arm_software = self.arm_software_map.get(arm, set())
        return arm_software.issubset(tested_software)

    def get_covered_arms(self, tested_software: Set[str]) -> Set[str]:
        """
        Получить множество всех АРМ, покрытых данным набором ПО

        Args:
            tested_software: Множество протестированного ПО

        Returns:
            Множество идентификаторов покрытых АРМ
        """
        covered = set()
        for arm, software_set in self.arm_software_map.items():
            if software_set.issubset(tested_software):
                covered.add(arm)
        return covered
