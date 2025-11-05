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
from exporter import Exporter
from tabs import tabs
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
if 'exporter' not in st.session_state:
    st.session_state.exporter = None
# Кэш для загруженных файлов (чтобы не перечитывать при смене колонок)
if 'uploaded_df' not in st.session_state:
    st.session_state.uploaded_df = None  # Заголовки
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None
if 'uploaded_df_full' not in st.session_state:
    st.session_state.uploaded_df_full = None  # Полный файл (после обработки)
if 'tested_df_preview' not in st.session_state:
    st.session_state.tested_df_preview = None  # Заголовки
if 'tested_file_name' not in st.session_state:
    st.session_state.tested_file_name = None
if 'tested_df_full' not in st.session_state:
    st.session_state.tested_df_full = None  # Полный файл (после загрузки)

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
    
    # Очистка кэша при удалении или смене файла
    if uploaded_file is None:
        # Файл удалён - очищаем весь кэш
        if st.session_state.uploaded_df is not None:
            st.session_state.uploaded_df = None
            st.session_state.uploaded_df_full = None
            st.session_state.uploaded_file_name = None
    elif st.session_state.uploaded_file_name is not None and uploaded_file.name != st.session_state.uploaded_file_name:
        # Файл сменился - очищаем весь кэш
        st.session_state.uploaded_df = None
        st.session_state.uploaded_df_full = None
        st.session_state.uploaded_file_name = None
    
    tested_software_file = st.file_uploader(
        "Выберите файл с протестированным ПО (опционально)",
        type=['xlsx', 'xls', 'csv'],
        help="Файл со списком уже протестированного ПО. Расчёт будет выполнен без учёта уже протестированного ПО, информация о том, протестированно ПО или нет, будет просто присоединена на этапе экспорта.",
        key="tested_software_file"
    )
    
    # Очистка кэша при удалении или смене файла с протестированным ПО
    if tested_software_file is None:
        # Файл удалён - очищаем весь кэш
        if st.session_state.tested_df_preview is not None:
            st.session_state.tested_df_preview = None
            st.session_state.tested_df_full = None
            st.session_state.tested_file_name = None
    elif st.session_state.tested_file_name is not None and tested_software_file.name != st.session_state.tested_file_name:
        # Файл сменился - очищаем весь кэш
        st.session_state.tested_df_preview = None
        st.session_state.tested_df_full = None
        st.session_state.tested_file_name = None
    
    # Выбор столбцов для файла с протестированным ПО (если загружен)
    tested_software_column = None
    tested_status_column = None
    if tested_software_file is not None:
        st.subheader("Выбор столбцов файла с протестированным ПО")
        
        st.info(f"📄 Файл выбран: {tested_software_file.name}")
        
        # Загружаем только заголовки для выбора колонок (быстро, без полной загрузки)
        if st.session_state.tested_df_preview is None:
            with st.spinner("Чтение заголовков..."):
                if tested_software_file.name.endswith('.csv'):
                    # Читаем только первую строку для получения заголовков
                    tested_df_preview = pd.read_csv(tested_software_file, encoding='utf-8-sig', nrows=0)
                else:
                    # Читаем только первую строку для получения заголовков
                    try:
                        tested_df_preview = pd.read_excel(tested_software_file, sheet_name='ПО', nrows=0)
                    except:
                        tested_df_preview = pd.read_excel(tested_software_file, nrows=0)
                
                # Кэшируем заголовки
                st.session_state.tested_df_preview = tested_df_preview
                st.session_state.tested_file_name = tested_software_file.name
        else:
            # Используем кэшированные заголовки
            tested_df_preview = st.session_state.tested_df_preview
        
        tested_columns = tested_df_preview.columns.tolist()
        
        tested_software_column = st.selectbox(
            "Столбец с наименованием ПО",
            options=tested_columns,
            index=tested_columns.index("Программное обеспечение")
                if "Программное обеспечение" in tested_columns 
                else (tested_columns.index("ПО для тестирования") if "ПО для тестирования" in tested_columns else 0),
            help="Название программного обеспечения в файле с протестированным ПО",
            key="software_column_tested"
        )
        
        tested_status_column = st.selectbox(
            "Столбец со статусом тестирования",
            options=tested_columns,
            index=tested_columns.index("ПО протестировано")
                if "ПО протестировано" in tested_columns 
                else (tested_columns.index("Статус") if "Статус" in tested_columns else 0),
            help="Столбец, указывающий, протестировано",
            key="status_column_tested"
        )
        
        # Кнопка для загрузки протестированного ПО в БД
        if st.button("🗄️ Загрузить список протестированного ПО в БД", key="export_tested_software_db_sidebar", type="primary"):
            with st.spinner("Загрузка файла с протестированным ПО..."):
                # ЗДЕСЬ загружаем полный файл с протестированным ПО (если еще не загружен)
                if st.session_state.tested_df_full is None or st.session_state.tested_file_name != tested_software_file.name:
                    # Загружаем полный файл первый раз или если файл сменился
                    if tested_software_file.name.endswith('.csv'):
                        tested_df_full = pd.read_csv(tested_software_file, encoding='utf-8-sig')
                    else:
                        try:
                            tested_df_full = pd.read_excel(tested_software_file, sheet_name='ПО')
                        except:
                            tested_df_full = pd.read_excel(tested_software_file)
                    
                    # Кэшируем полный файл
                    st.session_state.tested_df_full = tested_df_full
                else:
                    # Используем кэшированный полный файл
                    tested_df_full = st.session_state.tested_df_full
                
                # Берем ВСЕ столбцы и убираем строки с пустыми значениями в столбце ПО
                tested_df_clean = tested_df_full.dropna(subset=[tested_software_column])
                
                # Создаем Excel буфер
                import io
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    tested_df_clean.to_excel(writer, sheet_name='Протестированное ПО', index=False)
                excel_buffer.seek(0)
                st.session_state.excel_buffer_tested_software = excel_buffer
            
            # Импортируем модальное окно
            from modal_db import show_db_export_modal
            import os
            from dotenv import load_dotenv
            
            # Загружаем переменные окружения
            load_dotenv()
            
            # Callback для экспорта
            def export_callback(excel_buffer, schema, table, user, password, if_exists):
                from exporter import Exporter
                host = os.getenv('DB_HOST', 'localhost')
                port = os.getenv('DB_PORT', '5432')
                database = os.getenv('DB_NAME', 'postgres')
                Exporter.export_excel_to_database(
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
                excel_buffer=st.session_state.excel_buffer_tested_software,
                filename="tested_software.xlsx",
                on_export_callback=export_callback,
                default_schema=default_schema
            )

    if uploaded_file:
        try:
            st.info(f"📄 Файл выбран: {uploaded_file.name}")
            
            # Загружаем только заголовки для выбора колонок (быстро, без полной загрузки)
            if st.session_state.uploaded_df is None:
                with st.spinner("Чтение заголовков..."):
                    if uploaded_file.name.endswith('.csv'):
                        # Читаем только первую строку для получения заголовков
                        df = pd.read_csv(uploaded_file, encoding='utf-8-sig', nrows=0)
                    else:
                        # Читаем только первую строку для получения заголовков
                        df = pd.read_excel(uploaded_file, nrows=0)
                    
                    # Кэшируем только заголовки (не весь файл!)
                    st.session_state.uploaded_df = df
                    st.session_state.uploaded_file_name = uploaded_file.name
            else:
                # Используем кэшированные заголовки
                df = st.session_state.uploaded_df

            # Выбор столбцов для основного файла
            st.subheader("Выбор столбцов основного файла")

            columns = df.columns.tolist()

            arm_column = st.selectbox(
                "Столбец с устройством/пользователем",
                options=columns,
                index=columns.index("Устройство.Сетевое Имя устройства (уст-во, хост)")
                    if "Устройство.Сетевое Имя устройства (уст-во, хост)" in columns else 0,
                help="Идентификатор рабочей станции или пользователя",
                key="arm_column_main"
            )

            software_column = st.selectbox(
                "Столбец с наименованием ПО",
                options=columns,
                index=columns.index("Программное обеспечение")
                    if "Программное обеспечение" in columns else 0,
                help="Название программного обеспечения",
                key="software_column_main"
            )
            
            # Если загружен файл с протестированным ПО, нужно выбрать столбец с семейством ПО для маппинга
            software_family_column = None
            if tested_software_file is not None:
                software_family_column = st.selectbox(
                    "Столбец с семейством ПО (для маппинга с протестированным ПО)",
                    options=columns,
                    index=columns.index("Программное обеспечение.Семейство")
                        if "Программное обеспечение.Семейство" in columns 
                        else (2 if len(columns) > 2 else 0),
                    help="Столбец с семейством ПО, значения которого совпадают с ascupo_name в файле маппинга",
                    key="software_family_column_main"
                )
            
            # Кнопка обработки данных
            if st.button("📊 Обработать данные", type="primary", width="stretch"):
                with st.spinner("Загрузка и обработка данных..."):
                    # ЗДЕСЬ загружаем полный файл (если еще не загружен или файл сменился)
                    if st.session_state.uploaded_df_full is None:
                        # Загружаем полный файл
                        if uploaded_file.name.endswith('.csv'):
                            df_full = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                        else:
                            df_full = pd.read_excel(uploaded_file)
                        
                        # Кэшируем полный файл
                        st.session_state.uploaded_df_full = df_full
                    else:
                        # Используем кэшированный полный файл
                        df_full = st.session_state.uploaded_df_full
                    
                    # Обработка основного файла с пользователями
                    processor = DataProcessor(df_full, arm_column, software_column)
                    processor.process()

                    # Обработка файла с протестированным ПО (если загружен)
                    if tested_software_file is not None and tested_software_column is not None and tested_status_column is not None:
                        try:
                            # Загрузка файла с протестированным ПО (если еще не загружен или файл сменился)
                            if st.session_state.tested_df_full is None:
                                # Загружаем полный файл
                                if tested_software_file.name.endswith('.csv'):
                                    tested_df = pd.read_csv(tested_software_file, encoding='utf-8-sig')
                                else:
                                    # Пытаемся прочитать лист "ПО", если не найден - читаем первый лист
                                    try:
                                        tested_df = pd.read_excel(tested_software_file, sheet_name='ПО')
                                    except:
                                        tested_df = pd.read_excel(tested_software_file)
                                
                                # Кэшируем полный файл
                                st.session_state.tested_df_full = tested_df
                            else:
                                # Используем кэшированный полный файл
                                tested_df = st.session_state.tested_df_full
                            
                            # Оставляем ВСЕ столбцы и убираем строки с пустыми значениями в столбце ПО
                            tested_df_clean = tested_df.dropna(subset=[tested_software_column])
                            
                            st.session_state.tested_software_df = tested_df_clean
                            st.session_state.tested_software_column = tested_software_column
                            st.session_state.tested_status_column = tested_status_column
                            st.session_state.tested_software_file_name = tested_software_file.name
                            st.session_state.software_family_column = software_family_column
                            
                        except Exception as e:
                            st.warning(f"⚠️ Ошибка при загрузке файла с протестированным ПО: {e}")
                            st.session_state.tested_software_df = None
                            st.session_state.tested_software_column = None
                            st.session_state.tested_status_column = None
                            st.session_state.tested_software_file_name = None
                            st.session_state.software_family_column = None
                    else:
                        st.session_state.tested_software_df = None
                        st.session_state.tested_software_column = None
                        st.session_state.tested_status_column = None
                        st.session_state.tested_software_file_name = None
                        st.session_state.software_family_column = None

                    st.session_state.processor = processor
                    st.session_state.data_loaded = True
                    st.session_state.optimizer = MigrationOptimizer(processor)
                    st.session_state.exporter = Exporter(processor)

                    st.success("✓ Данные обработаны!")
                    st.rerun()

        except Exception as e:
            st.error(f"❌ Ошибка при загрузке файла: {e}")

# Основной контент
if st.session_state.data_loaded:
    processor = st.session_state.processor
    optimizer = st.session_state.optimizer
    exporter = st.session_state.exporter

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
    
    # Информация о протестированном ПО
    if 'tested_software_file_name' in st.session_state and st.session_state.tested_software_file_name is not None:
        tested_count = len(st.session_state.tested_software_df) if 'tested_software_df' in st.session_state and st.session_state.tested_software_df is not None else 0
        st.info(f"📋 Загружен файл с протестированным ПО: **{st.session_state.tested_software_file_name}** ({tested_count} ПО)")

    # Вкладки для разных режимов
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Ручной режим (эвристика)", 
        "🔬 Ручной режим (точный)", 
        "👥 Миграция N пользователей (эвристика)",
        "🔬 Миграция N пользователей (точный)"
    ])

    tabs(tab1, tab2, tab3, tab4, st, processor, optimizer, uploaded_file, exporter)

   

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