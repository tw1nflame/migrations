"""
Оптимизатор волн миграции ПО на Linux
Streamlit приложение для анализа и планирования миграции рабочих станций
"""

import streamlit as st
import pandas as pd
import io
from typing import Dict, Set, Tuple, List
from optimizer import MigrationOptimizer
from data_processor import DataProcessor

# Настройка страницы
st.set_page_config(
    page_title="Оптимизатор миграции ПО",
    page_icon="🐧",
    layout="wide"
)

st.title("🐧 Оптимизатор волн миграции ПО на Linux")
st.markdown("""
Это приложение помогает оптимизировать планирование миграции рабочих станций с Windows на Linux
путём анализа установленного ПО и расчёта оптимальных волн тестирования.
""")

# Инициализация session_state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'optimizer' not in st.session_state:
    st.session_state.optimizer = None
if 'processor' not in st.session_state:
    st.session_state.processor = None

# Sidebar для загрузки данных
with st.sidebar:
    st.header("⚙️ Настройки")

    # Загрузка файла
    st.subheader("1. Загрузка данных")
    uploaded_file = st.file_uploader(
        "Выберите Excel или CSV файл",
        type=['xlsx', 'xls', 'csv'],
        help="Файл должен содержать столбцы с устройствами и установленным ПО"
    )

    if uploaded_file is not None:
        try:
            # Загрузка данных
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            else:
                df = pd.read_excel(uploaded_file)

            st.success(f"✓ Файл загружен: {uploaded_file.name}")
            st.info(f"Строк: {len(df)}")

            # Выбор столбцов
            st.subheader("2. Выбор столбцов")

            columns = df.columns.tolist()

            arm_column = st.selectbox(
                "Столбец с устройством/пользователем",
                options=columns,
                index=columns.index("Устройство.Сетевое Имя устройства (уст-во, хост)")
                    if "Устройство.Сетевое Имя устройства (уст-во, хост)" in columns else 0,
                help="Идентификатор рабочей станции или пользователя"
            )

            software_column = st.selectbox(
                "Столбец с наименованием ПО",
                options=columns,
                index=columns.index("Программное обеспечение")
                    if "Программное обеспечение" in columns else 0,
                help="Название программного обеспечения"
            )

            # Кнопка обработки данных
            if st.button("📊 Обработать данные", type="primary"):
                with st.spinner("Обработка данных..."):
                    processor = DataProcessor(df, arm_column, software_column)
                    processor.process()

                    st.session_state.processor = processor
                    st.session_state.data_loaded = True
                    st.session_state.optimizer = MigrationOptimizer(processor)

                    st.success("✓ Данные обработаны!")
                    st.rerun()

        except Exception as e:
            st.error(f"❌ Ошибка при загрузке файла: {e}")

# Основной контент
if st.session_state.data_loaded:
    processor = st.session_state.processor
    optimizer = st.session_state.optimizer

    # Общая статистика
    st.header("📈 Общая статистика")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Всего АРМ", processor.total_arms)
    with col2:
        st.metric("Уникальное ПО", processor.total_software)
    with col3:
        st.metric("Уникальных наборов ПО", len(processor.set_to_arms_map))
    with col4:
        avg_software = sum(len(s) for s in processor.arm_software_map.values()) / len(processor.arm_software_map)
        st.metric("Среднее ПО на АРМ", f"{avg_software:.1f}")

    # Вкладки для разных режимов
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Ручной режим (эвристика)", 
        "🔬 Ручной режим (точный)", 
        "👥 Миграция N пользователей (эвристика)",
        "🔬 Миграция N пользователей (точный)"
    ])

    with tab1:
        st.subheader("Планирование волн миграции (эвристический алгоритм)")
        st.markdown("""
        Укажите количество волн и лимиты ПО для тестирования в каждой волне.
        **Эвристический алгоритм** быстро находит хорошее решение, выбирая на каждом шаге оптимальное ПО.
        """)

        col1, col2 = st.columns([1, 2])

        with col1:
            num_waves_greedy = st.number_input(
                "Количество волн",
                min_value=1,
                max_value=10,
                value=3,
                help="Сколько волн тестирования планируется",
                key="num_waves_greedy"
            )

        st.markdown("**Лимиты ПО для каждой волны:**")

        wave_limits_greedy = []
        cols = st.columns(min(num_waves_greedy, 3))
        for i in range(num_waves_greedy):
            col_idx = i % 3
            with cols[col_idx]:
                limit = st.number_input(
                    f"Волна {i+1}",
                    min_value=1,
                    max_value=processor.total_software,
                    value=min(100, processor.total_software),
                    key=f"wave_limit_greedy_{i}"
                )
                wave_limits_greedy.append(limit)

        if st.button("🚀 Рассчитать волны (эвристика)", type="primary", key="calc_greedy"):
            with st.spinner("Расчёт оптимальных волн миграции (эвристический алгоритм)..."):
                results = optimizer.calculate_waves(wave_limits_greedy, use_ilp=False)
                st.session_state.wave_results_greedy = results
                st.success("✓ Расчёт завершён!")
                st.rerun()

        # Отображение результатов
        if 'wave_results_greedy' in st.session_state:
            results = st.session_state.wave_results_greedy

            st.markdown("---")
            st.subheader("📊 Результаты расчёта")

            # Таблица по волнам
            wave_stats = []
            cumulative_arms = 0
            cumulative_software = 0

            for i, wave_data in enumerate(results['waves']):
                cumulative_arms += wave_data['arms_migrated']
                cumulative_software += wave_data['software_selected']

                wave_stats.append({
                    'Волна': i + 1,
                    'Лимит ПО': wave_limits_greedy[i],
                    'Выбрано ПО': wave_data['software_selected'],
                    'АРМ в волне': wave_data['arms_migrated'],
                    'АРМ накопительно': cumulative_arms
                })

            # Итоговая строка
            wave_stats.append({
                'Волна': 'Всего',
                'Лимит ПО': sum(wave_limits_greedy),
                'Выбрано ПО': cumulative_software,
                'АРМ в волне': '-',
                'АРМ накопительно': cumulative_arms
            })

            st.dataframe(
                pd.DataFrame(wave_stats),
                use_container_width=True,
                hide_index=True
            )

            # Визуализация
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Покрытие АРМ**")
                coverage_pct = (cumulative_arms / processor.total_arms) * 100
                st.progress(cumulative_arms / processor.total_arms)
                st.metric(
                    "Процент покрытия",
                    f"{coverage_pct:.1f}%",
                    f"{cumulative_arms} из {processor.total_arms} АРМ"
                )

            with col2:
                st.markdown("**Использование ПО**")
                software_pct = (cumulative_software / processor.total_software) * 100
                st.progress(cumulative_software / processor.total_software)
                st.metric(
                    "ПО в плане",
                    f"{software_pct:.1f}%",
                    f"{cumulative_software} из {processor.total_software} ПО"
                )

            # Кнопка экспорта
            st.markdown("---")
            if st.button("💾 Экспортировать результаты в Excel", key="export_greedy"):
                with st.spinner("Создание Excel файла..."):
                    excel_buffer = optimizer.export_to_excel(results, uploaded_file.name)

                    st.download_button(
                        label="⬇️ Скачать migration_plan_result_greedy.xlsx",
                        data=excel_buffer,
                        file_name="migration_plan_result_greedy.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    with tab2:
        st.subheader("Планирование волн миграции (точный алгоритм)")
        st.markdown("""
        Укажите количество волн и лимиты ПО для тестирования в каждой волне.
        **Точный ILP алгоритм** находит оптимальное решение, но может работать медленнее на больших данных.
        """)

        col1, col2 = st.columns([1, 2])

        with col1:
            num_waves_ilp = st.number_input(
                "Количество волн",
                min_value=1,
                max_value=10,
                value=3,
                help="Сколько волн тестирования планируется",
                key="num_waves_ilp"
            )

        st.markdown("**Лимиты ПО для каждой волны:**")

        wave_limits_ilp = []
        cols = st.columns(min(num_waves_ilp, 3))
        for i in range(num_waves_ilp):
            col_idx = i % 3
            with cols[col_idx]:
                limit = st.number_input(
                    f"Волна {i+1}",
                    min_value=1,
                    max_value=processor.total_software,
                    value=min(100, processor.total_software),
                    key=f"wave_limit_ilp_{i}"
                )
                wave_limits_ilp.append(limit)

        if st.button("🚀 Рассчитать волны (точный)", type="primary", key="calc_ilp"):
            with st.spinner("Расчёт оптимальных волн миграции (точный ILP алгоритм)..."):
                results = optimizer.calculate_waves(wave_limits_ilp, use_ilp=True)
                st.session_state.wave_results_ilp = results
                st.success("✓ Расчёт завершён!")
                st.rerun()

        # Отображение результатов
        if 'wave_results_ilp' in st.session_state:
            results = st.session_state.wave_results_ilp

            st.markdown("---")
            st.subheader("📊 Результаты расчёта")

            # Таблица по волнам
            wave_stats = []
            cumulative_arms = 0
            cumulative_software = 0

            for i, wave_data in enumerate(results['waves']):
                cumulative_arms += wave_data['arms_migrated']
                cumulative_software += wave_data['software_selected']

                wave_stats.append({
                    'Волна': i + 1,
                    'Лимит ПО': wave_limits_ilp[i],
                    'Выбрано ПО': wave_data['software_selected'],
                    'АРМ в волне': wave_data['arms_migrated'],
                    'АРМ накопительно': cumulative_arms
                })

            # Итоговая строка
            wave_stats.append({
                'Волна': 'Всего',
                'Лимит ПО': sum(wave_limits_ilp),
                'Выбрано ПО': cumulative_software,
                'АРМ в волне': '-',
                'АРМ накопительно': cumulative_arms
            })

            st.dataframe(
                pd.DataFrame(wave_stats),
                use_container_width=True,
                hide_index=True
            )

            # Визуализация
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Покрытие АРМ**")
                coverage_pct = (cumulative_arms / processor.total_arms) * 100
                st.progress(cumulative_arms / processor.total_arms)
                st.metric(
                    "Процент покрытия",
                    f"{coverage_pct:.1f}%",
                    f"{cumulative_arms} из {processor.total_arms} АРМ"
                )

            with col2:
                st.markdown("**Использование ПО**")
                software_pct = (cumulative_software / processor.total_software) * 100
                st.progress(cumulative_software / processor.total_software)
                st.metric(
                    "ПО в плане",
                    f"{software_pct:.1f}%",
                    f"{cumulative_software} из {processor.total_software} ПО"
                )

            # Кнопка экспорта
            st.markdown("---")
            if st.button("💾 Экспортировать результаты в Excel", key="export_ilp"):
                with st.spinner("Создание Excel файла..."):
                    excel_buffer = optimizer.export_to_excel(results, uploaded_file.name)

                    st.download_button(
                        label="⬇️ Скачать migration_plan_result_ilp.xlsx",
                        data=excel_buffer,
                        file_name="migration_plan_result_ilp.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    with tab3:
        st.subheader("Автоматические рекомендации")
        st.markdown("""
        Система автоматически рассчитывает оптимальные параметры для первых двух волн миграции.
        """)

        if st.button("🤖 Рассчитать рекомендации", type="primary"):
            with st.spinner("Расчёт автоматических рекомендаций..."):
                auto_results = optimizer.calculate_auto_recommendations()
                st.session_state.auto_results = auto_results
                st.success("✓ Рекомендации готовы!")
                st.rerun()

        if 'auto_results' in st.session_state:
            auto = st.session_state.auto_results

            st.markdown("---")

            # Волна 1
            st.subheader("🌊 Волна 1")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Минимальный набор (20% АРМ)**")
                st.metric("ПО для тестирования", auto['wave1_min']['software_count'])
                st.metric("АРМ мигрирует", auto['wave1_min']['arms_count'])

            with col2:
                st.markdown("**Оптимальный набор (100 ПО)**")
                st.metric("ПО для тестирования", auto['wave1_opt']['software_count'])
                st.metric("АРМ мигрирует", auto['wave1_opt']['arms_count'])

            # Волна 2
            st.subheader("🌊 Волна 2 (после Волны 1 оптимальной)")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Оптимальный набор (100 ПО)**")
                st.metric("ПО для тестирования", auto['wave2_opt']['software_count'])
                st.metric("Дополнительно АРМ", auto['wave2_opt']['arms_count'])

            with col2:
                st.markdown("**Итого за 2 волны**")
                total_software = auto['wave1_opt']['software_count'] + auto['wave2_opt']['software_count']
                total_arms = auto['wave1_opt']['arms_count'] + auto['wave2_opt']['arms_count']
                st.metric("Всего ПО", total_software)
                st.metric("Всего АРМ", total_arms)

    with tab3:
        st.subheader("Расчёт минимального ПО для миграции N пользователей (эвристический алгоритм)")
        st.markdown("""
        Введите целевое количество пользователей, и **эвристический алгоритм** быстро найдёт минимальный набор ПО, 
        который покрывает любых N пользователей из вашей базы.
        """)

        col1, col2 = st.columns([1, 2])

        with col1:
            target_users_greedy = st.number_input(
                "Количество пользователей для покрытия",
                min_value=1,
                max_value=processor.total_arms,
                value=min(100, processor.total_arms),
                help="Сколько пользователей нужно покрыть минимальным набором ПО",
                key="target_users_greedy"
            )

        if st.button("🔍 Найти минимальное ПО (эвристика)", type="primary", key="find_min_software_greedy"):
            with st.spinner(f"Поиск минимального набора ПО для покрытия {target_users_greedy} пользователей (эвристический алгоритм)..."):
                min_software, covered_arms = optimizer.find_minimum_software_for_coverage(
                    target_arms_count=target_users_greedy,
                    use_ilp=False
                )
                
                st.session_state.min_coverage_results_greedy = {
                    'target_users': target_users_greedy,
                    'software_set': min_software,
                    'covered_arms': covered_arms,
                    'software_count': len(min_software),
                    'actual_coverage': len(covered_arms)
                }
                st.success("✓ Расчёт завершён!")
                st.rerun()

        # Отображение результатов
        if 'min_coverage_results_greedy' in st.session_state:
            results = st.session_state.min_coverage_results_greedy

            st.markdown("---")
            st.subheader("📊 Результаты расчёта")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Целевое количество АРМ",
                    results['target_users']
                )

            with col2:
                st.metric(
                    "Минимальное ПО для покрытия",
                    results['software_count']
                )

            with col3:
                st.metric(
                    "Фактически покрыто АРМ",
                    results['actual_coverage']
                )

            # Процент покрытия
            coverage_pct = (results['actual_coverage'] / processor.total_arms) * 100
            st.markdown("**Покрытие от общего числа АРМ**")
            st.progress(results['actual_coverage'] / processor.total_arms)
            st.info(f"📈 {coverage_pct:.1f}% от всех АРМ ({results['actual_coverage']} из {processor.total_arms})")

            # Эффективность
            efficiency = results['actual_coverage'] / results['software_count'] if results['software_count'] > 0 else 0
            st.markdown("**Эффективность**")
            st.success(f"🎯 В среднем {efficiency:.1f} АРМ на одно ПО")

            # Детальная информация
            with st.expander("📋 Список ПО для тестирования"):
                software_list = sorted(list(results['software_set']))
                for i, software in enumerate(software_list, 1):
                    st.text(f"{i}. {software}")

            with st.expander("👥 Список покрытых АРМ"):
                arms_list = sorted(list(results['covered_arms']))
                for i, arm in enumerate(arms_list, 1):
                    st.text(f"{i}. {arm}")

    with tab4:
        st.subheader("Расчёт минимального ПО для миграции N пользователей (точный алгоритм)")
        st.markdown("""
        Введите целевое количество пользователей, и **точный ILP алгоритм** найдёт оптимальный минимальный набор ПО, 
        который покрывает любых N пользователей из вашей базы.
        """)

        col1, col2 = st.columns([1, 2])

        with col1:
            target_users_ilp = st.number_input(
                "Количество пользователей для покрытия",
                min_value=1,
                max_value=processor.total_arms,
                value=min(100, processor.total_arms),
                help="Сколько пользователей нужно покрыть минимальным набором ПО",
                key="target_users_ilp"
            )

        if st.button("🔍 Найти минимальное ПО (точный)", type="primary", key="find_min_software_ilp"):
            with st.spinner(f"Поиск минимального набора ПО для покрытия {target_users_ilp} пользователей (точный ILP алгоритм)..."):
                min_software, covered_arms = optimizer.find_minimum_software_for_coverage(
                    target_arms_count=target_users_ilp,
                    use_ilp=True
                )
                
                st.session_state.min_coverage_results_ilp = {
                    'target_users': target_users_ilp,
                    'software_set': min_software,
                    'covered_arms': covered_arms,
                    'software_count': len(min_software),
                    'actual_coverage': len(covered_arms)
                }
                st.success("✓ Расчёт завершён!")
                st.rerun()

        # Отображение результатов
        if 'min_coverage_results_ilp' in st.session_state:
            results = st.session_state.min_coverage_results_ilp

            st.markdown("---")
            st.subheader("📊 Результаты расчёта")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Целевое количество АРМ",
                    results['target_users']
                )

            with col2:
                st.metric(
                    "Минимальное ПО для покрытия",
                    results['software_count']
                )

            with col3:
                st.metric(
                    "Фактически покрыто АРМ",
                    results['actual_coverage']
                )

            # Процент покрытия
            coverage_pct = (results['actual_coverage'] / processor.total_arms) * 100
            st.markdown("**Покрытие от общего числа АРМ**")
            st.progress(results['actual_coverage'] / processor.total_arms)
            st.info(f"📈 {coverage_pct:.1f}% от всех АРМ ({results['actual_coverage']} из {processor.total_arms})")

            # Эффективность
            efficiency = results['actual_coverage'] / results['software_count'] if results['software_count'] > 0 else 0
            st.markdown("**Эффективность**")
            st.success(f"🎯 В среднем {efficiency:.1f} АРМ на одно ПО")

            # Детальная информация
            with st.expander("📋 Список ПО для тестирования"):
                software_list = sorted(list(results['software_set']))
                for i, software in enumerate(software_list, 1):
                    st.text(f"{i}. {software}")

            with st.expander("👥 Список покрытых АРМ"):
                arms_list = sorted(list(results['covered_arms']))
                for i, arm in enumerate(arms_list, 1):
                    st.text(f"{i}. {arm}")

else:
    # Инструкция для начала работы
    st.info("👈 Загрузите файл с данными в боковой панели для начала работы")

    st.markdown("""
    ### Как использовать приложение:

    1. **Загрузите файл** - Excel (.xlsx) или CSV с данными об установленном ПО
    2. **Выберите столбцы** - укажите столбец с устройствами и столбец с ПО
    3. **Обработайте данные** - нажмите кнопку для анализа
    4. **Выберите режим**:
       - **Ручной** - задайте количество волн и лимиты
       - **Автоматический** - получите рекомендации системы
    5. **Экспортируйте результаты** - сохраните план миграции в Excel

    ### Формат данных:

    Файл должен содержать минимум два столбца:
    - Идентификатор устройства/пользователя
    - Наименование установленного ПО
    """)