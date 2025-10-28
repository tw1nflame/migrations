"""
Тестирование модулей приложения
"""

import sys
import pandas as pd
from data_processor import DataProcessor
from optimizer import MigrationOptimizer

# Установка кодировки UTF-8 для Windows консоли
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_basic_functionality():
    """Базовое тестирование функциональности"""

    print("=" * 60)
    print("ТЕСТИРОВАНИЕ МОДУЛЕЙ ОПТИМИЗАТОРА МИГРАЦИИ")
    print("=" * 60)

    # Загрузка тестовых данных
    print("\n1. Загрузка данных...")
    try:
        df = pd.read_excel("по_на_устройстве_09_07_2025_16_25_КГМК.xlsx")
        print(f"   [OK] Загружено строк: {len(df)}")
    except Exception as e:
        print(f"   [ERROR] Ошибка загрузки: {e}")
        return

    # Обработка данных
    print("\n2. Обработка данных...")
    try:
        processor = DataProcessor(
            df,
            "Устройство.Сетевое Имя устройства (уст-во, хост)",
            "Программное обеспечение"
        )
        processor.process()

        print(f"   [OK] Всего АРМ: {processor.total_arms}")
        print(f"   [OK] Всего уникального ПО: {processor.total_software}")
        print(f"   [OK] Уникальных наборов ПО: {len(processor.set_to_arms_map)}")

        # Статистика по наборам
        avg_software = sum(len(s) for s in processor.arm_software_map.values()) / len(processor.arm_software_map)
        print(f"   [OK] Среднее ПО на АРМ: {avg_software:.1f}")

    except Exception as e:
        print(f"   [ERROR] Ошибка обработки: {e}")
        import traceback
        traceback.print_exc()
        return

    # Тест оптимизатора
    print("\n3. Тестирование оптимизатора...")
    try:
        optimizer = MigrationOptimizer(processor)

        # Тест: найти ПО для миграции 10% АРМ
        print("\n   Тест: минимальный набор для 10% АРМ")
        target = int(processor.total_arms * 0.1)
        software_set, arms_set = optimizer.find_minimum_software_for_coverage(target)
        print(f"   [OK] Для миграции {len(arms_set)} АРМ нужно {len(software_set)} ПО")

        # Тест: расчёт волн
        print("\n   Тест: расчёт 2 волн по 50 ПО")
        results = optimizer.calculate_waves([50, 50])
        print(f"   [OK] Волна 1: {results['waves'][0]['software_selected']} ПО, "
              f"{results['waves'][0]['arms_migrated']} АРМ")
        print(f"   [OK] Волна 2: {results['waves'][1]['software_selected']} ПО, "
              f"{results['waves'][1]['arms_migrated']} АРМ")
        print(f"   [OK] Всего мигрировано: {results['total_migrated_arms']} АРМ")

        # Тест: автоматические рекомендации
        print("\n   Тест: автоматические рекомендации")
        auto = optimizer.calculate_auto_recommendations()
        print(f"   [OK] Минимум для 20% АРМ: {auto['wave1_min']['software_count']} ПО -> "
              f"{auto['wave1_min']['arms_count']} АРМ")
        print(f"   [OK] Оптимум 100 ПО (волна 1): {auto['wave1_opt']['software_count']} ПО -> "
              f"{auto['wave1_opt']['arms_count']} АРМ")
        print(f"   [OK] Оптимум 100 ПО (волна 2): {auto['wave2_opt']['software_count']} ПО -> "
              f"{auto['wave2_opt']['arms_count']} АРМ")

    except Exception as e:
        print(f"   [ERROR] Ошибка оптимизации: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 60)
    print("[SUCCESS] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 60)
    print("\nДля запуска приложения выполните:")
    print("  streamlit run app.py")
    print("или")
    print("  run.bat")

if __name__ == "__main__":
    test_basic_functionality()
