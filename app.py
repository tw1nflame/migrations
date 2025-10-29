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

    # Загрузка файлов
    st.subheader("1. Загрузка данных")
    
    uploaded_file = st.file_uploader(
        "Выберите файл с пользователями",
        type=['xlsx', 'xls', 'csv'],
        help="Файл должен содержать столбцы с устройствами и установленным ПО",
        key="users_file"
    )
    
    # tested_software_file = st.file_uploader(
    #     "Выберите файл с протестированным ПО (опционально)",
    #     type=['xlsx', 'xls', 'csv'],
    #     help="Файл со списком уже протестированного ПО. Если не указан, расчёт будет выполнен без учёта уже протестированного ПО.",
    #     key="tested_software_file"
    # )
    tested_software_file = None  # Временно отключено

    if uploaded_file is not None:
        try:
            # Загрузка данных
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            else:
                df = pd.read_excel(uploaded_file)

            st.success(f"✓ Файл загружен: {uploaded_file.name}")
            st.info(f"Строк: {len(df)}")
            
            # Информация о файле с протестированным ПО (временно отключено)
            # if tested_software_file is not None:
            #     st.success(f"✓ Файл с протестированным ПО загружен: {tested_software_file.name}")
            # else:
            #     st.info("ℹ️ Файл с протестированным ПО не загружен")

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
                    # Обработка основного файла с пользователями
                    processor = DataProcessor(df, arm_column, software_column)
                    processor.process()

                    # Обработка файла с протестированным ПО (если загружен)
                    tested_software_set = set()
                    if tested_software_file is not None:
                        try:
                            # Загрузка файла с протестированным ПО
                            if tested_software_file.name.endswith('.csv'):
                                tested_df = pd.read_csv(tested_software_file, encoding='utf-8-sig')
                            else:
                                tested_df = pd.read_excel(tested_software_file)
                            
                            # Извлечение списка протестированного ПО
                            # Ожидаем, что в файле есть столбец с названием ПО
                            # Пытаемся найти подходящий столбец
                            possible_columns = ['Программное обеспечение', 'ПО', 'Software', 'ПО для тестирования']
                            software_col = None
                            
                            for col in possible_columns:
                                if col in tested_df.columns:
                                    software_col = col
                                    break
                            
                            # Если не нашли стандартные названия, берем первый столбец
                            if software_col is None:
                                software_col = tested_df.columns[0]
                            
                            # Извлекаем уникальные значения ПО, исключая пустые
                            tested_software_set = set(tested_df[software_col].dropna().unique())
                            
                            st.session_state.tested_software_df = tested_df
                            st.session_state.tested_software_file_name = tested_software_file.name
                            st.session_state.tested_software_set = tested_software_set
                            
                        except Exception as e:
                            st.warning(f"⚠️ Ошибка при загрузке файла с протестированным ПО: {e}")
                            st.session_state.tested_software_df = None
                            st.session_state.tested_software_file_name = None
                            st.session_state.tested_software_set = set()
                    else:
                        st.session_state.tested_software_df = None
                        st.session_state.tested_software_file_name = None
                        st.session_state.tested_software_set = set()

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
    
    # Информация о протестированном ПО (временно отключено)
    # if 'tested_software_file_name' in st.session_state and st.session_state.tested_software_file_name is not None:
    #     tested_count = len(st.session_state.tested_software_set) if 'tested_software_set' in st.session_state else 0
    #     st.info(f"📋 Загружен файл с протестированным ПО: **{st.session_state.tested_software_file_name}** ({tested_count} ПО)")

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
                    'Волна': str(i + 1),  # Преобразуем в строку
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
                'АРМ в волне': None,  # None вместо пустой строки
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

            # Детальная информация по волнам
            st.markdown("---")
            st.subheader("📋 Детальная информация по волнам")
            
            for i, wave_data in enumerate(results['waves']):
                wave_num = wave_data['wave_number']
                with st.expander(f"🌊 Волна {wave_num} - {wave_data['software_selected']} ПО, {wave_data['arms_migrated']} АРМ"):
                    # Кнопки экспорта вверху
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        # Экспорт списка ПО
                        tested_software_set = st.session_state.get('tested_software_set', set())
                        output_sw = optimizer.create_software_export(
                            wave_data['software_list'],
                            tested_software_set,
                            f'Волна {wave_num}'
                        )
                        
                        st.download_button(
                            label=f"📦 Скачать ПО волны {wave_num}",
                            data=output_sw,
                            file_name=f"wave_{wave_num}_software_heuristic.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_sw_{wave_num}_greedy",
                            use_container_width=True
                        )
                    
                    with col_btn2:
                        # Экспорт списка АРМов
                        output_arms = optimizer.create_arms_export(
                            wave_data['arms_list'],
                            f'Волна {wave_num}'
                        )
                        
                        st.download_button(
                            label=f"👥 Скачать АРМ волны {wave_num}",
                            data=output_arms,
                            file_name=f"wave_{wave_num}_arms_heuristic.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_arms_{wave_num}_greedy",
                            use_container_width=True
                        )
                    
                    st.markdown("---")
                    
                    # Списки
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**ПО для тестирования ({wave_data['software_selected']})**")
                        software_list = sorted(wave_data['software_list'])
                        for j, software in enumerate(software_list, 1):
                            st.text(f"{j}. {software}")
                    
                    with col2:
                        st.markdown(f"**Мигрирующие АРМ ({wave_data['arms_migrated']})**")
                        arms_list = sorted(wave_data['arms_list'])
                        for j, arm in enumerate(arms_list, 1):
                            st.text(f"{j}. {arm}")

            # Кнопка экспорта
            st.markdown("---")
            if st.button("💾 Экспортировать результаты в Excel", key="export_greedy"):
                with st.spinner("Создание Excel файла..."):
                    tested_software_set = st.session_state.get('tested_software_set', set())
                    excel_buffer = optimizer.export_to_excel(results, uploaded_file.name, tested_software_set)

                    st.download_button(
                        label="⬇️ Скачать migration_plan_result_heuristic.xlsx",
                        data=excel_buffer,
                        file_name="migration_plan_result_heuristic.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    with tab2:
        st.subheader("Планирование волн миграции (точный алгоритм)")
        st.markdown("""
        Укажите количество волн и лимиты ПО для тестирования в каждой волне.
        **Точный ILP алгоритм** находит оптимальное решение, но может работать медленнее на больших данных.
        
        ⚠️ **Контроль времени работы:** Ограничение времени останавливает алгоритм до нахождения оптимального решения.
        В этом случае будет возвращено лучшее найденное допустимое решение, которое может быть **неоптимальным** 
        (т.е. не гарантируется максимум мигрирующих АРМов при заданном лимите ПО).
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
            
            time_limit_ilp = st.number_input(
                "Лимит времени (сек)",
                min_value=0,
                max_value=3600,
                value=300,
                help="Максимальное время работы решателя для каждой волны (0 = без ограничения). При ограничении времени решение может быть неоптимальным.",
                key="time_limit_ilp"
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
                time_limit_value = time_limit_ilp if time_limit_ilp > 0 else None
                results = optimizer.calculate_waves(wave_limits_ilp, use_ilp=True, time_limit=time_limit_value)
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
                    'Волна': str(i + 1),  # Преобразуем в строку
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
                'АРМ в волне': None,  # None вместо пустой строки
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

            # Детальная информация по волнам
            st.markdown("---")
            st.subheader("📋 Детальная информация по волнам")
            
            for i, wave_data in enumerate(results['waves']):
                wave_num = wave_data['wave_number']
                with st.expander(f"🌊 Волна {wave_num} - {wave_data['software_selected']} ПО, {wave_data['arms_migrated']} АРМ"):
                    # Кнопки экспорта вверху
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        # Экспорт списка ПО
                        tested_software_set = st.session_state.get('tested_software_set', set())
                        output_sw = optimizer.create_software_export(
                            wave_data['software_list'],
                            tested_software_set,
                            f'Волна {wave_num}'
                        )
                        
                        st.download_button(
                            label=f"📦 Скачать ПО волны {wave_num}",
                            data=output_sw,
                            file_name=f"wave_{wave_num}_software_ilp.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_sw_{wave_num}_ilp",
                            use_container_width=True
                        )
                    
                    with col_btn2:
                        # Экспорт списка АРМов
                        output_arms = optimizer.create_arms_export(
                            wave_data['arms_list'],
                            f'Волна {wave_num}'
                        )
                        
                        st.download_button(
                            label=f"👥 Скачать АРМ волны {wave_num}",
                            data=output_arms,
                            file_name=f"wave_{wave_num}_arms_ilp.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_arms_{wave_num}_ilp",
                            use_container_width=True
                        )
                    
                    st.markdown("---")
                    
                    # Списки
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**ПО для тестирования ({wave_data['software_selected']})**")
                        software_list = sorted(wave_data['software_list'])
                        for j, software in enumerate(software_list, 1):
                            st.text(f"{j}. {software}")
                    
                    with col2:
                        st.markdown(f"**Мигрирующие АРМ ({wave_data['arms_migrated']})**")
                        arms_list = sorted(wave_data['arms_list'])
                        for j, arm in enumerate(arms_list, 1):
                            st.text(f"{j}. {arm}")

            # Кнопка экспорта
            st.markdown("---")
            if st.button("💾 Экспортировать результаты в Excel", key="export_ilp"):
                with st.spinner("Создание Excel файла..."):
                    tested_software_set = st.session_state.get('tested_software_set', set())
                    excel_buffer = optimizer.export_to_excel(results, uploaded_file.name, tested_software_set)

                    st.download_button(
                        label="⬇️ Скачать migration_plan_result_ilp.xlsx",
                        data=excel_buffer,
                        file_name="migration_plan_result_ilp.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    # with tab3:
    #     st.subheader("Автоматические рекомендации")
    #     st.markdown("""
    #     Система автоматически рассчитывает оптимальные параметры для первых двух волн миграции.
    #     """)

    #     if st.button("🤖 Рассчитать рекомендации", type="primary"):
    #         with st.spinner("Расчёт автоматических рекомендаций..."):
    #             auto_results = optimizer.calculate_auto_recommendations()
    #             st.session_state.auto_results = auto_results
    #             st.success("✓ Рекомендации готовы!")
    #             st.rerun()

    #     if 'auto_results' in st.session_state:
    #         auto = st.session_state.auto_results

    #         st.markdown("---")

    #         # Волна 1
    #         st.subheader("🌊 Волна 1")
    #         col1, col2 = st.columns(2)

    #         with col1:
    #             st.markdown("**Минимальный набор (20% АРМ)**")
    #             st.metric("ПО для тестирования", auto['wave1_min']['software_count'])
    #             st.metric("АРМ мигрирует", auto['wave1_min']['arms_count'])

    #         with col2:
    #             st.markdown("**Оптимальный набор (100 ПО)**")
    #             st.metric("ПО для тестирования", auto['wave1_opt']['software_count'])
    #             st.metric("АРМ мигрирует", auto['wave1_opt']['arms_count'])

    #         # Волна 2
    #         st.subheader("🌊 Волна 2 (после Волны 1 оптимальной)")
    #         col1, col2 = st.columns(2)

    #         with col1:
    #             st.markdown("**Оптимальный набор (100 ПО)**")
    #             st.metric("ПО для тестирования", auto['wave2_opt']['software_count'])
    #             st.metric("Дополнительно АРМ", auto['wave2_opt']['arms_count'])

    #         with col2:
    #             st.markdown("**Итого за 2 волны**")
    #             total_software = auto['wave1_opt']['software_count'] + auto['wave2_opt']['software_count']
    #             total_arms = auto['wave1_opt']['arms_count'] + auto['wave2_opt']['arms_count']
    #             st.metric("Всего ПО", total_software)
    #             st.metric("Всего АРМ", total_arms)

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
            st.markdown("---")
            st.subheader("📋 Детальная информация")
            
            # Кнопки экспорта вверху
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                # Экспорт списка ПО
                tested_software_set = st.session_state.get('tested_software_set', set())
                output_sw = optimizer.create_software_export(
                    list(results['software_set']),
                    tested_software_set,
                    'ПО'
                )
                
                st.download_button(
                    label="📦 Скачать список ПО",
                    data=output_sw,
                    file_name="n_users_software_heuristic.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_sw_n_users_greedy",
                    use_container_width=True
                )
            
            with col_btn2:
                # Экспорт списка АРМов
                output_arms = optimizer.create_arms_export(
                    list(results['covered_arms']),
                    'АРМ'
                )
                
                st.download_button(
                    label="👥 Скачать список АРМ",
                    data=output_arms,
                    file_name="n_users_arms_heuristic.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_arms_n_users_greedy",
                    use_container_width=True
                )
            
            st.markdown("---")
            
            # Списки в expandере
            with st.expander("📋 Показать списки ПО и АРМ"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**ПО для тестирования ({results['software_count']})**")
                    software_list = sorted(list(results['software_set']))
                    for i, software in enumerate(software_list, 1):
                        st.text(f"{i}. {software}")
                
                with col2:
                    st.markdown(f"**Покрытые АРМ ({results['actual_coverage']})**")
                    arms_list = sorted(list(results['covered_arms']))
                    for i, arm in enumerate(arms_list, 1):
                        st.text(f"{i}. {arm}")

            # Кнопка экспорта полного отчета
            st.markdown("---")
            if st.button("💾 Экспортировать полный отчет в Excel", key="export_min_coverage_greedy"):
                with st.spinner("Создание Excel файла..."):
                    # Формируем данные в формате, совместимом с export_to_excel
                    export_results = {
                        'waves': [{
                            'wave_number': 1,
                            'software_selected': results['software_count'],
                            'software_list': list(results['software_set']),
                            'arms_migrated': results['actual_coverage'],
                            'arms_list': list(results['covered_arms'])
                        }],
                        'total_tested_software': results['software_count'],
                        'total_migrated_arms': results['actual_coverage'],
                        'software_wave_map': {sw: 1 for sw in results['software_set']},
                        'arm_wave_map': {arm: 1 for arm in results['covered_arms']},
                        'tested_software': results['software_set'],
                        'migrated_arms': results['covered_arms']
                    }
                    
                    tested_software_set = st.session_state.get('tested_software_set', set())
                    excel_buffer = optimizer.export_to_excel(export_results, uploaded_file.name, tested_software_set)

                    st.download_button(
                        label="⬇️ Скачать migration_n_users_heuristic.xlsx",
                        data=excel_buffer,
                        file_name="migration_n_users_heuristic.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    with tab4:
        st.subheader("Расчёт минимального ПО для миграции N пользователей (точный алгоритм)")
        st.markdown("""
        Введите целевое количество пользователей, и **точный ILP алгоритм** найдёт оптимальный минимальный набор ПО, 
        который покрывает любых N пользователей из вашей базы.
        
        ⚠️ **Контроль времени работы:** Ограничение времени останавливает алгоритм до нахождения оптимального решения.
        В этом случае будет возвращено лучшее найденное допустимое решение, которое может быть **неоптимальным** 
        (т.е. может потребоваться больше ПО, чем в истинно оптимальном решении).
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
            
            time_limit_n_users_ilp = st.number_input(
                "Лимит времени (сек)",
                min_value=0,
                max_value=3600,
                value=600,
                help="Максимальное время работы решателя (0 = без ограничения). При ограничении времени решение может быть неоптимальным.",
                key="time_limit_n_users_ilp"
            )

        if st.button("🔍 Найти минимальное ПО (точный)", type="primary", key="find_min_software_ilp"):
            with st.spinner(f"Поиск минимального набора ПО для покрытия {target_users_ilp} пользователей (точный ILP алгоритм)..."):
                time_limit_value = time_limit_n_users_ilp if time_limit_n_users_ilp > 0 else None
                min_software, covered_arms = optimizer.find_minimum_software_for_coverage(
                    target_arms_count=target_users_ilp,
                    use_ilp=True,
                    time_limit=time_limit_value
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
            st.markdown("---")
            st.subheader("📋 Детальная информация")
            
            # Кнопки экспорта вверху
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                # Экспорт списка ПО
                tested_software_set = st.session_state.get('tested_software_set', set())
                output_sw = optimizer.create_software_export(
                    list(results['software_set']),
                    tested_software_set,
                    'ПО'
                )
                
                st.download_button(
                    label="📦 Скачать список ПО",
                    data=output_sw,
                    file_name="n_users_software_ilp.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_sw_n_users_ilp",
                    use_container_width=True
                )
            
            with col_btn2:
                # Экспорт списка АРМов
                output_arms = optimizer.create_arms_export(
                    list(results['covered_arms']),
                    'АРМ'
                )
                
                st.download_button(
                    label="👥 Скачать список АРМ",
                    data=output_arms,
                    file_name="n_users_arms_ilp.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_arms_n_users_ilp",
                    use_container_width=True
                )
            
            st.markdown("---")
            
            # Списки в expandере
            with st.expander("📋 Показать списки ПО и АРМ"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**ПО для тестирования ({results['software_count']})**")
                    software_list = sorted(list(results['software_set']))
                    for i, software in enumerate(software_list, 1):
                        st.text(f"{i}. {software}")
                
                with col2:
                    st.markdown(f"**Покрытые АРМ ({results['actual_coverage']})**")
                    arms_list = sorted(list(results['covered_arms']))
                    for i, arm in enumerate(arms_list, 1):
                        st.text(f"{i}. {arm}")

            # Кнопка экспорта полного отчета
            st.markdown("---")
            if st.button("💾 Экспортировать полный отчет в Excel", key="export_min_coverage_ilp"):
                with st.spinner("Создание Excel файла..."):
                    # Формируем данные в формате, совместимом с export_to_excel
                    export_results = {
                        'waves': [{
                            'wave_number': 1,
                            'software_selected': results['software_count'],
                            'software_list': list(results['software_set']),
                            'arms_migrated': results['actual_coverage'],
                            'arms_list': list(results['covered_arms'])
                        }],
                        'total_tested_software': results['software_count'],
                        'total_migrated_arms': results['actual_coverage'],
                        'software_wave_map': {sw: 1 for sw in results['software_set']},
                        'arm_wave_map': {arm: 1 for arm in results['covered_arms']},
                        'tested_software': results['software_set'],
                        'migrated_arms': results['covered_arms']
                    }
                    
                    tested_software_set = st.session_state.get('tested_software_set', set())
                    excel_buffer = optimizer.export_to_excel(export_results, uploaded_file.name, tested_software_set)

                    st.download_button(
                        label="⬇️ Скачать migration_n_users_ilp.xlsx",
                        data=excel_buffer,
                        file_name="migration_n_users_ilp.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

else:
    # Инструкция для начала работы
    st.info("👈 Загрузите файл с данными в боковой панели для начала работы")

    st.markdown("""
    ### Как использовать приложение:

    1. **Загрузите файл** - Excel (.xlsx, .xls) или CSV с данными об установленном ПО
    2. **Выберите столбцы** - укажите столбец с устройствами и столбец с ПО
    3. **Обработайте данные** - нажмите кнопку для анализа
    4. **Выберите режим**:
       - **Ручной (эвристика)** - быстрый расчет оптимальных волн
       - **Ручной (точный)** - математически оптимальное решение через целочисленное линейное программирование (ILP) - может работать дольше, но дает гарантированно лучший результат. Если ограничить по времени, то вернет наилучшее приближение к гарантированному результату.
       - **Миграция N пользователей (эвристика)** - быстрый поиск минимального ПО
       - **Миграция N пользователей (точный)** - оптимальный минимальный набор ПО через целочисленное линейное программирование (ILP) - работает долго (в некоторых условиях 5-15 минут), но гарантированно дает оптимальный результат. Если ограничить по времени, то вернет наилучшее приближение к гарантированному результату.
    5. **Экспортируйте результаты** - сохраните план миграции в Excel

    ### 📊 Формат данных:

    **Требования к файлу:**
    - Файл должен содержать минимум два столбца:
      - **Идентификатор устройства/пользователя** (например: "Устройство", "Компьютер")
      - **Наименование установленного ПО** (например: "Программное обеспечение", "ПО")
    - Все остальные столбцы будут проигнорированы и просто добавлены в итоговый файл.
    
    **Пример структуры таблицы:**
    
    | Устройство | Программное обеспечение |
    |------------|-------------------------|
    | PC-001     | Microsoft Office 2016   |
    | PC-001     | Google Chrome           |
    | PC-001     | Adobe Acrobat Reader    |
    | PC-002     | Microsoft Office 2016   |
    | PC-002     | VLC Media Player        |
    | PC-002     | 7-Zip                   |
    | PC-003     | Google Chrome           |
    | PC-003     | VLC Media Player        |
    
    ⚠️ **Важно:** Каждая строка = одна связка "АРМ ↔ ПО". Если у АРМа установлено 5 программ, в таблице должно быть 5 строк для этого АРМа.
    """)