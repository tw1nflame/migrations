"""
Интерфейс алгоритмов по миграции ПО
"""

import pandas as pd

def tabs(tab1, tab2, tab3, tab4, st, processor, optimizer, uploaded_file, exporter):

    with tab1:
        st.subheader("Планирование волн миграции (эвристический алгоритм)")
        st.markdown("""
        Укажите количество волн и лимиты ПО для тестирования в каждой волне.
        
        **Эвристический алгоритм** быстро находит хорошее решение, выбирая на каждом шаге оптимальное ПО.
        
        ⚠️ *Примечание: Эвристический метод не гарантирует оптимальное решение, но дает достаточно хорошее решение за короткое время.*
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
                width="stretch",
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
                        tested_software_df = st.session_state.get('tested_software_df', None)
                        tested_software_column = st.session_state.get('tested_software_column', None)
                        software_family_column = st.session_state.get('software_family_column', None)
                        output_sw = exporter.create_software_export(
                            wave_data['software_list'],
                            tested_software_df,
                            tested_software_column,
                            processor.original_df,
                            processor.software_column,
                            software_family_column,
                            f'Волна {wave_num}'
                        )
                        
                        st.download_button(
                            label=f"📦 Скачать ПО волны {wave_num}",
                            data=output_sw,
                            file_name=f"wave_{wave_num}_software_heuristic.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_sw_{wave_num}_greedy",
                            width="stretch"
                        )
                    
                    with col_btn2:
                        # Экспорт списка АРМов
                        output_arms = exporter.create_arms_export(
                            wave_data['arms_list'],
                            f'Волна {wave_num}'
                        )
                        
                        st.download_button(
                            label=f"👥 Скачать АРМ волны {wave_num}",
                            data=output_arms,
                            file_name=f"wave_{wave_num}_arms_heuristic.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_arms_{wave_num}_greedy",
                            width="stretch"
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
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                if st.button("💾 Экспортировать результаты в Excel", key="export_greedy", width="stretch"):
                    try:
                        with st.spinner("Создание Excel файла..."):
                            tested_software_df = st.session_state.get('tested_software_df', None)
                            tested_software_column = st.session_state.get('tested_software_column', None)
                            software_family_column = st.session_state.get('software_family_column', None)
                            excel_buffer = exporter.export_to_excel(results, uploaded_file.name, tested_software_df, tested_software_column, software_family_column)
                            st.session_state.excel_buffer_greedy = excel_buffer
                            st.session_state.show_download_greedy = True
                            st.success("✓ Excel файл готов к скачиванию!")
                    except Exception as e:
                        st.error(f"❌ Ошибка при создании Excel файла: {str(e)}")

                if st.session_state.get('show_download_greedy', False):
                    st.download_button(
                        label="⬇️ Скачать migration_plan_result_heuristic.xlsx",
                        data=st.session_state.excel_buffer_greedy,
                        file_name="migration_plan_result_heuristic.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_btn_greedy"
                    )
            
            with col_export2:
                if st.button("🗄️ Загрузить в базу данных", key="export_db_greedy", width="stretch"):
                    # Создаем Excel буфер, если его еще нет
                    if 'excel_buffer_greedy' not in st.session_state:
                        with st.spinner("Создание Excel файла..."):
                            tested_software_df = st.session_state.get('tested_software_df', None)
                            tested_software_column = st.session_state.get('tested_software_column', None)
                            software_family_column = st.session_state.get('software_family_column', None)
                            excel_buffer = exporter.export_to_excel(results, uploaded_file.name, tested_software_df, tested_software_column, software_family_column)
                            st.session_state.excel_buffer_greedy = excel_buffer
                    
                    # Импортируем модальное окно
                    from modal_db import show_db_export_modal
                    import os
                    from dotenv import load_dotenv
                    
                    # Загружаем переменные окружения
                    load_dotenv()
                    
                    # Функция обратного вызова для экспорта
                    def export_callback(excel_buffer, schema, table, user, password, if_exists):
                        host = os.getenv('DB_HOST', 'localhost')
                        port = os.getenv('DB_PORT', '5432')
                        database = os.getenv('DB_NAME', 'postgres')
                        exporter.export_excel_to_database(
                            excel_buffer=excel_buffer,
                            schema=schema,
                            table=table,
                            user=user,
                            password=password,
                            host=host,
                            port=port,
                            database=database,
                            if_exists=if_exists
                        )
                    
                    # Показываем модальное окно
                    default_schema = os.getenv('DB_SCHEMA', 'public')
                    show_db_export_modal(
                        excel_buffer=st.session_state.excel_buffer_greedy,
                        filename="migration_plan_result_heuristic.xlsx",
                        on_export_callback=export_callback,
                        default_schema=default_schema
                    )

    with tab2:
        st.subheader("Планирование волн миграции (точный алгоритм)")
        st.markdown("""
        Укажите количество волн и лимиты ПО для тестирования в каждой волне.
        
        **Точный ILP алгоритм** находит математически оптимальное решение, гарантируя максимальное покрытие АРМ при заданных лимитах ПО.
        
        ✅ *Преимущество: Гарантирует оптимальное решение. Недостаток: Может работать медленнее на больших данных.*
        
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
                max_value=13600,
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
                width="stretch",
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
                        tested_software_df = st.session_state.get('tested_software_df', None)
                        tested_software_column = st.session_state.get('tested_software_column', None)
                        software_family_column = st.session_state.get('software_family_column', None)
                        output_sw = exporter.create_software_export(
                            wave_data['software_list'],
                            tested_software_df,
                            tested_software_column,
                            processor.original_df,
                            processor.software_column,
                            software_family_column,
                            f'Волна {wave_num}'
                        )
                        
                        st.download_button(
                            label=f"📦 Скачать ПО волны {wave_num}",
                            data=output_sw,
                            file_name=f"wave_{wave_num}_software_ilp.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_sw_{wave_num}_ilp",
                            width="stretch"
                        )
                    
                    with col_btn2:
                        # Экспорт списка АРМов
                        output_arms = exporter.create_arms_export(
                            wave_data['arms_list'],
                            f'Волна {wave_num}'
                        )
                        
                        st.download_button(
                            label=f"👥 Скачать АРМ волны {wave_num}",
                            data=output_arms,
                            file_name=f"wave_{wave_num}_arms_ilp.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_arms_{wave_num}_ilp",
                            width="stretch"
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
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                if st.button("💾 Экспортировать результаты в Excel", key="export_ilp", width="stretch"):
                    try:
                        with st.spinner("Создание Excel файла..."):
                            tested_software_df = st.session_state.get('tested_software_df', None)
                            tested_software_column = st.session_state.get('tested_software_column', None)
                            software_family_column = st.session_state.get('software_family_column', None)
                            excel_buffer = exporter.export_to_excel(results, uploaded_file.name, tested_software_df, tested_software_column, software_family_column)
                            st.session_state.excel_buffer_ilp = excel_buffer
                            st.session_state.show_download_ilp = True
                            st.success("✓ Excel файл готов к скачиванию!")
                    except Exception as e:
                        st.error(f"❌ Ошибка при создании Excel файла: {str(e)}")

                if st.session_state.get('show_download_ilp', False):
                    st.download_button(
                        label="⬇️ Скачать migration_plan_result_ilp.xlsx",
                        data=st.session_state.excel_buffer_ilp,
                        file_name="migration_plan_result_ilp.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_btn_ilp"
                    )
            
            with col_export2:
                if st.button("🗄️ Загрузить в базу данных", key="export_db_ilp", width="stretch"):
                    # Создаем Excel буфер, если его еще нет
                    if 'excel_buffer_ilp' not in st.session_state:
                        with st.spinner("Создание Excel файла..."):
                            tested_software_df = st.session_state.get('tested_software_df', None)
                            tested_software_column = st.session_state.get('tested_software_column', None)
                            software_family_column = st.session_state.get('software_family_column', None)
                            excel_buffer = exporter.export_to_excel(results, uploaded_file.name, tested_software_df, tested_software_column, software_family_column)
                            st.session_state.excel_buffer_ilp = excel_buffer
                    
                    # Импортируем модальное окно
                    from modal_db import show_db_export_modal
                    import os
                    from dotenv import load_dotenv
                    
                    # Загружаем переменные окружения
                    load_dotenv()
                    
                    # Функция обратного вызова для экспорта
                    def export_callback(excel_buffer, schema, table, user, password, if_exists):
                        host = os.getenv('DB_HOST', 'localhost')
                        port = os.getenv('DB_PORT', '5432')
                        database = os.getenv('DB_NAME', 'postgres')
                        exporter.export_excel_to_database(
                            excel_buffer=excel_buffer,
                            schema=schema,
                            table=table,
                            user=user,
                            password=password,
                            host=host,
                            port=port,
                            database=database,
                            if_exists=if_exists
                        )
                    
                    # Показываем модальное окно
                    default_schema = os.getenv('DB_SCHEMA', 'public')
                    show_db_export_modal(
                        excel_buffer=st.session_state.excel_buffer_ilp,
                        filename="migration_plan_result_ilp.xlsx",
                        on_export_callback=export_callback,
                        default_schema=default_schema
                    )

    with tab3:
        st.subheader("Расчёт минимального ПО для миграции N пользователей (эвристический алгоритм)")
        st.markdown("""
        Введите целевое количество пользователей, и **эвристический алгоритм** быстро найдёт набор ПО, 
        который покрывает любых N пользователей из вашей базы, и постарается сделать его минимальным.
        
        ⚠️ *Примечание: Эвристический метод не гарантирует оптимальное решение, но дает достаточно хорошее решение за короткое время.*
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
                tested_software_df = st.session_state.get('tested_software_df', None)
                tested_software_column = st.session_state.get('tested_software_column', None)
                software_family_column = st.session_state.get('software_family_column', None)
                output_sw = exporter.create_software_export(
                    list(results['software_set']),
                    tested_software_df,
                    tested_software_column,
                    processor.original_df,
                    processor.software_column,
                    software_family_column,
                    'ПО'
                )
                
                st.download_button(
                    label="📦 Скачать список ПО",
                    data=output_sw,
                    file_name="n_users_software_heuristic.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_sw_n_users_greedy",
                    width="stretch"
                )
            
            with col_btn2:
                # Экспорт списка АРМов
                output_arms = exporter.create_arms_export(
                    list(results['covered_arms']),
                    'АРМ'
                )
                
                st.download_button(
                    label="👥 Скачать список АРМ",
                    data=output_arms,
                    file_name="n_users_arms_heuristic.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_arms_n_users_greedy",
                    width="stretch"
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
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                if st.button("💾 Экспортировать полный отчет в Excel", key="export_min_coverage_greedy", width="stretch"):
                    try:
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
                            
                            tested_software_df = st.session_state.get('tested_software_df', None)
                            tested_software_column = st.session_state.get('tested_software_column', None)
                            software_family_column = st.session_state.get('software_family_column', None)
                            excel_buffer = exporter.export_to_excel(export_results, uploaded_file.name, tested_software_df, tested_software_column, software_family_column)
                            st.session_state.excel_buffer_n_users_greedy = excel_buffer
                            st.session_state.show_download_n_users_greedy = True
                            st.success("✓ Excel файл готов к скачиванию!")
                    except Exception as e:
                        st.error(f"❌ Ошибка при создании Excel файла: {str(e)}")

                if st.session_state.get('show_download_n_users_greedy', False):
                    st.download_button(
                        label="⬇️ Скачать migration_n_users_heuristic.xlsx",
                        data=st.session_state.excel_buffer_n_users_greedy,
                        file_name="migration_n_users_heuristic.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_btn_n_users_greedy"
                    )
            
            with col_export2:
                if st.button("🗄️ Загрузить в базу данных", key="export_db_n_users_greedy", width="stretch"):
                    # Создаем Excel буфер, если его еще нет
                    if 'excel_buffer_n_users_greedy' not in st.session_state:
                        with st.spinner("Создание Excel файла..."):
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
                            tested_software_df = st.session_state.get('tested_software_df', None)
                            tested_software_column = st.session_state.get('tested_software_column', None)
                            software_family_column = st.session_state.get('software_family_column', None)
                            excel_buffer = exporter.export_to_excel(export_results, uploaded_file.name, tested_software_df, tested_software_column, software_family_column)
                            st.session_state.excel_buffer_n_users_greedy = excel_buffer
                    
                    # Импортируем модальное окно
                    from modal_db import show_db_export_modal
                    import os
                    from dotenv import load_dotenv
                    
                    # Загружаем переменные окружения
                    load_dotenv()
                    
                    # Функция обратного вызова для экспорта
                    def export_callback(excel_buffer, schema, table, user, password, if_exists):
                        host = os.getenv('DB_HOST', 'localhost')
                        port = os.getenv('DB_PORT', '5432')
                        database = os.getenv('DB_NAME', 'postgres')
                        exporter.export_excel_to_database(
                            excel_buffer=excel_buffer,
                            schema=schema,
                            table=table,
                            user=user,
                            password=password,
                            host=host,
                            port=port,
                            database=database,
                            if_exists=if_exists
                        )
                    
                    # Показываем модальное окно
                    default_schema = os.getenv('DB_SCHEMA', 'public')
                    show_db_export_modal(
                        excel_buffer=st.session_state.excel_buffer_n_users_greedy,
                        filename="migration_n_users_heuristic.xlsx",
                        on_export_callback=export_callback,
                        default_schema=default_schema
                    )

    with tab4:
        st.subheader("Расчёт минимального ПО для миграции N пользователей (точный алгоритм)")
        st.markdown("""
        Введите целевое количество пользователей, и **точный ILP алгоритм** найдёт минимальный набор ПО, 
        который покрывает любых N пользователей из вашей базы.
        
        ✅ *Преимущество: Гарантирует минимальное количество ПО. Недостаток: Может работать медленнее на больших данных.*
        
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
                max_value=13600,
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
                tested_software_df = st.session_state.get('tested_software_df', None)
                tested_software_column = st.session_state.get('tested_software_column', None)
                software_family_column = st.session_state.get('software_family_column', None)
                output_sw = exporter.create_software_export(
                    list(results['software_set']),
                    tested_software_df,
                    tested_software_column,
                    processor.original_df,
                    processor.software_column,
                    software_family_column,
                    'ПО'
                )
                
                st.download_button(
                    label="📦 Скачать список ПО",
                    data=output_sw,
                    file_name="n_users_software_ilp.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_sw_n_users_ilp",
                    width="stretch"
                )
            
            with col_btn2:
                # Экспорт списка АРМов
                output_arms = exporter.create_arms_export(
                    list(results['covered_arms']),
                    'АРМ'
                )
                
                st.download_button(
                    label="👥 Скачать список АРМ",
                    data=output_arms,
                    file_name="n_users_arms_ilp.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_arms_n_users_ilp",
                    width="stretch"
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
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                if st.button("💾 Экспортировать полный отчет в Excel", key="export_min_coverage_ilp", width="stretch"):
                    try:
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
                            
                            tested_software_df = st.session_state.get('tested_software_df', None)
                            tested_software_column = st.session_state.get('tested_software_column', None)
                            software_family_column = st.session_state.get('software_family_column', None)
                            excel_buffer = exporter.export_to_excel(export_results, uploaded_file.name, tested_software_df, tested_software_column, software_family_column)
                            st.session_state.excel_buffer_n_users_ilp = excel_buffer
                            st.session_state.show_download_n_users_ilp = True
                            st.success("✓ Excel файл готов к скачиванию!")
                    except Exception as e:
                        st.error(f"❌ Ошибка при создании Excel файла: {str(e)}")

                if st.session_state.get('show_download_n_users_ilp', False):
                    st.download_button(
                        label="⬇️ Скачать migration_n_users_ilp.xlsx",
                        data=st.session_state.excel_buffer_n_users_ilp,
                        file_name="migration_n_users_ilp.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_btn_n_users_ilp"
                    )
            
            with col_export2:
                if st.button("🗄️ Загрузить в базу данных", key="export_db_n_users_ilp", width="stretch"):
                    # Создаем Excel буфер, если его еще нет
                    if 'excel_buffer_n_users_ilp' not in st.session_state:
                        with st.spinner("Создание Excel файла..."):
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
                            tested_software_df = st.session_state.get('tested_software_df', None)
                            tested_software_column = st.session_state.get('tested_software_column', None)
                            software_family_column = st.session_state.get('software_family_column', None)
                            excel_buffer = exporter.export_to_excel(export_results, uploaded_file.name, tested_software_df, tested_software_column, software_family_column)
                            st.session_state.excel_buffer_n_users_ilp = excel_buffer
                    
                    # Импортируем модальное окно
                    from modal_db import show_db_export_modal
                    import os
                    from dotenv import load_dotenv
                    
                    # Загружаем переменные окружения
                    load_dotenv()
                    
                    # Функция обратного вызова для экспорта
                    def export_callback(excel_buffer, schema, table, user, password, if_exists):
                        host = os.getenv('DB_HOST', 'localhost')
                        port = os.getenv('DB_PORT', '5432')
                        database = os.getenv('DB_NAME', 'postgres')
                        exporter.export_excel_to_database(
                            excel_buffer=excel_buffer,
                            schema=schema,
                            table=table,
                            user=user,
                            password=password,
                            host=host,
                            port=port,
                            database=database,
                            if_exists=if_exists
                        )
                    
                    # Показываем модальное окно
                    default_schema = os.getenv('DB_SCHEMA', 'public')
                    show_db_export_modal(
                        excel_buffer=st.session_state.excel_buffer_n_users_ilp,
                        filename="migration_n_users_ilp.xlsx",
                        on_export_callback=export_callback,
                        default_schema=default_schema
                    )