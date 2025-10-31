"""
Модуль для экспорта результатов в Excel
Содержит класс Exporter для создания различных отчетов
"""

import pandas as pd
import io
from typing import Dict, Set, List
from data_processor import DataProcessor


class Exporter:
    """
    Класс для экспорта результатов оптимизации в Excel файлы
    """

    def __init__(self, processor: DataProcessor):
        """
        Инициализация экспортера

        Args:
            processor: Экземпляр DataProcessor с обработанными данными
        """
        self.processor = processor

    def export_to_excel(
        self,
        results: Dict,
        original_filename: str,
        tested_software_df: pd.DataFrame = None,
        tested_software_column: str = None
    ) -> io.BytesIO:
        """
        Экспортировать результаты в Excel файл с тремя листами

        Args:
            results: Результаты расчёта волн
            original_filename: Имя исходного файла
            tested_software_df: DataFrame с протестированным ПО (столбцы: ПО, Статус)
            tested_software_column: Название столбца с ПО в tested_software_df

        Returns:
            BytesIO буфер с Excel файлом
        """
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист 1: "Data" - исходные данные + столбцы "Волна миграции" и опционально статус тестирования
            df_data = self.processor.original_df.copy()

            # Добавляем столбец с номером волны на основе АРМа (не ПО!)
            arm_wave_map = results.get('arm_wave_map', {})

            def get_wave(arm_name):
                return arm_wave_map.get(arm_name, None)  # None вместо 'N/A' для совместимости с БД

            df_data['Волна миграции'] = df_data[
                self.processor.arm_column  # Используем столбец с АРМ, а не ПО
            ].apply(get_wave)

            # Присоединяем статус тестирования через merge
            if tested_software_df is not None and not tested_software_df.empty and tested_software_column:
                df_data = df_data.merge(
                    tested_software_df,
                    left_on=self.processor.software_column,
                    right_on=tested_software_column,
                    how='left'
                )
                # Удаляем дублирующий столбец если он появился
                if tested_software_column != self.processor.software_column:
                    df_data = df_data.drop(columns=[tested_software_column])

            # Переименовываем ключевые колонки в стандартные имена
            rename_map = {
                self.processor.software_column: 'software_name',
                self.processor.arm_column: 'arm_id',
                'Волна миграции': 'wave'
            }
            
            # Если есть колонка статуса (второй столбец из tested_software_df), переименовываем её
            if tested_software_df is not None and not tested_software_df.empty and len(tested_software_df.columns) > 1:
                status_column = tested_software_df.columns[1]  # Второй столбец - статус
                if status_column in df_data.columns:
                    rename_map[status_column] = 'software_status'
            
            df_data = df_data.rename(columns=rename_map)
            
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
    def create_software_export(
        software_list: List[str],
        tested_software_df: pd.DataFrame = None,
        tested_software_column: str = None,
        sheet_name: str = 'ПО'
    ) -> io.BytesIO:
        """
        Создать Excel файл со списком ПО и статусом тестирования

        Args:
            software_list: Список ПО для экспорта
            tested_software_df: DataFrame с протестированным ПО (столбцы: ПО, Статус)
            tested_software_column: Название столбца с ПО в tested_software_df
            sheet_name: Название листа в Excel

        Returns:
            BytesIO буфер с Excel файлом
        """
        sorted_list = sorted(software_list)
        df_software = pd.DataFrame({
            'ПО для тестирования': sorted_list
        })

        # Присоединяем статус через merge если есть данные
        # Проверяем что это DataFrame, а не set (для обратной совместимости)
        if tested_software_df is not None and isinstance(tested_software_df, pd.DataFrame) and not tested_software_df.empty and tested_software_column:
            df_software = df_software.merge(
                tested_software_df,
                left_on='ПО для тестирования',
                right_on=tested_software_column,
                how='left'
            )
            # Удаляем дублирующий столбец если он появился
            if tested_software_column != 'ПО для тестирования':
                df_software = df_software.drop(columns=[tested_software_column])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_software.to_excel(writer, sheet_name=sheet_name, index=False)
        output.seek(0)
        return output

    @staticmethod
    def create_arms_export(
        arms_list: List[str],
        sheet_name: str = 'АРМ'
    ) -> io.BytesIO:
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

    @staticmethod
    def export_excel_to_database(
        excel_buffer: io.BytesIO,
        schema: str,
        table: str,
        user: str,
        password: str,
        host: str,
        port: str,
        database: str,
        if_exists: str = 'replace'
    ) -> None:
        """
        Экспортировать данные из Excel файла в базу данных PostgreSQL

        Args:
            excel_buffer: BytesIO буфер с Excel файлом
            schema: Схема базы данных
            table: Имя таблицы
            user: Логин пользователя БД
            password: Пароль пользователя БД
            host: Адрес сервера БД
            port: Порт БД (строка или число)
            database: Название базы данных
            if_exists: Действие при существующей таблице ('fail', 'replace', 'append')

        Raises:
            Exception: При ошибке подключения или экспорта
        """
        # Импорты лучше делать в начале файла, но для статического метода оставим здесь
        import pandas as pd
        from sqlalchemy import create_engine, text

        # ЛОГИРОВАНИЕ ПАРАМЕТРОВ В САМОМ НАЧАЛЕ
        print(f"\n{'='*60}")
        print(f"🔌 НАЧАЛО ЭКСПОРТА В БД")
        print(f"{'='*60}")
        print(f"Параметры подключения (полученные функцией):")
        print(f"  - host: '{host}' (type: {type(host).__name__})")
        print(f"  - port: '{port}' (type: {type(port).__name__}, repr: {repr(port)}, len: {len(str(port))})")
        print(f"  - database: '{database}' (type: {type(database).__name__})")
        print(f"  - schema: '{schema}'")
        print(f"  - table: '{table}'")
        print(f"  - user: '{user}'")
        print(f"  - if_exists: '{if_exists}'")
        # Проверка на скрытые символы в порте
        port_str = str(port)
        print(f"\nАнализ строки порта:")
        print(f"  - ASCII codes: {[ord(c) for c in port_str]}")
        print(f"  - После strip: '{port_str.strip()}' (len: {len(port_str.strip())})")
        print(f"{'='*60}\n")

        # Сброс указателя буфера в начало
        excel_buffer.seek(0)

        # Чтение всех листов из Excel
        excel_data = pd.read_excel(excel_buffer, sheet_name=None, engine='openpyxl')

        # Валидация и преобразование порта
        try:
            # Убираем пробелы и преобразуем в int
            port_str_cleaned = str(port).strip()
            print(f"🔧 Преобразование порта: '{port_str_cleaned}' -> int")
            port_int = int(port_str_cleaned)
            print(f"✅ Порт успешно преобразован: {port_int}")
            
            if port_int <= 0 or port_int > 65535:
                raise ValueError(f"Порт должен быть в диапазоне 1-65535, получено: {port_int}")
        except ValueError as e:
            print(f"❌ ОШИБКА преобразования порта!")
            print(f"   Исходное значение: '{port}' (type: {type(port).__name__})")
            print(f"   После strip: '{str(port).strip()}'")
            print(f"   Ошибка: {e}")
            raise ValueError(f"Некорректное значение порта '{port}': {e}") from e

        # Создание строки подключения
        connection_string = f"postgresql://{user}:{password}@{host}:{port_int}/{database}"
        engine = create_engine(connection_string)

        try:
            # Шаг 1: Убедимся, что схема существует.
            # Это лучше делать в отдельном соединении/транзакции перед циклом.
            with engine.connect() as connection:
                with connection.begin(): # Начинаем транзакцию для DDL
                    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

            # Шаг 2: Экспорт только первого листа в указанную таблицу
            # Берем первый лист из словаря
            first_sheet_name = list(excel_data.keys())[0]
            df = excel_data[first_sheet_name]
            
            print(f"📊 Экспорт данных в БД:")
            print(f"  - Лист: {first_sheet_name}")
            print(f"  - Строк: {len(df)}")
            print(f"  - Столбцов: {len(df.columns)}")
            print(f"  - Колонки: {list(df.columns)}")
            
            # Логируем типы данных ПЕРЕД обработкой
            print(f"\n🔍 Типы данных ПЕРЕД обработкой:")
            for col in df.columns:
                print(f"  - {col}: {df[col].dtype}, unique values: {df[col].nunique()}, null count: {df[col].isna().sum()}")
            
            # Заменяем пустые строки и NaN на None (NULL в SQL)
            df = df.replace('', None)
            df = df.replace('nan', None)
            df = df.where(pd.notna(df), None)  # Заменяем все NaN на None (pandas 2.0+)
            
            # Преобразуем все столбцы в строковый тип, чтобы избежать ошибок типов данных
            print(f"\n🔧 Преобразование столбцов в строки...")
            for col in df.columns:
                try:
                    original_dtype = df[col].dtype
                    df[col] = df[col].astype(str).replace('None', None).replace('nan', None).replace('NaN', None).replace('<NA>', None)
                    print(f"  ✅ {col}: {original_dtype} -> str")
                except Exception as col_error:
                    print(f"  ❌ Ошибка в колонке '{col}': {col_error}")
                    raise Exception(f"Ошибка преобразования колонки '{col}': {col_error}") from col_error
            
            # Логируем типы данных ПОСЛЕ обработки
            print(f"\n🔍 Типы данных ПОСЛЕ обработки:")
            for col in df.columns:
                print(f"  - {col}: {df[col].dtype}, null count: {df[col].isna().sum()}")
            
            # Показываем первые строки для отладки
            print(f"\n📋 Первые 3 строки данных:")
            print(df.head(3).to_string())
            
            # Экспортируем в таблицу с указанным именем (без суффикса)
            print(f"\n💾 Загрузка в PostgreSQL...")
            df.to_sql(
                name=table,
                con=engine,
                schema=schema,
                if_exists=if_exists,
                index=False,
                method='multi',
                chunksize=1000
            )
            print(f"✅ Данные успешно загружены в {schema}.{table}")

        except Exception as e:
            # Перехватываем исключение и выбрасываем его с более понятным сообщением
            import traceback
            error_details = traceback.format_exc()
            print(f"\n❌ ОШИБКА при экспорте:")
            print(error_details)
            raise Exception(f"Ошибка при экспорте в базу данных: {e}\n\nДетали:\n{error_details}") from e

        finally:
            # Важно освободить ресурсы движка после использования
            engine.dispose()