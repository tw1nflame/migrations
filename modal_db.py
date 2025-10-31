"""
Модуль модального окна для экспорта в базу данных
Содержит UI компонент для ввода параметров подключения к БД
"""

import streamlit as st


@st.dialog("Экспорт в базу данных PostgreSQL", width="large")
def show_db_export_modal(excel_buffer, filename: str, on_export_callback, default_schema: str = "public"):
    """
    Модальное окно для экспорта данных в PostgreSQL
    
    Args:
        excel_buffer: BytesIO объект с Excel файлом
        filename: Имя файла для отображения
        on_export_callback: Функция обратного вызова для экспорта (exporter, schema, table, user, password, host, port)
        default_schema: Схема по умолчанию (читается из .env)
    """
    st.markdown(f"**Файл для экспорта:** `{filename}`")
    st.markdown("---")
    
    # Поля ввода
    st.subheader("Параметры подключения")
    
    col1, col2 = st.columns(2)
    
    with col1:
        schema = st.text_input(
            "Схема базы данных",
            value=default_schema,
            placeholder="public",
            help="Название схемы в PostgreSQL (например: public, migration, etc.)"
        )
        
        user = st.text_input(
            "Логин пользователя БД",
            placeholder="postgres",
            help="Имя пользователя для подключения к базе данных"
        )
    
    with col2:
        table = st.text_input(
            "Имя таблицы",
            placeholder="migration_data",
            help="Название таблицы, в которую будут загружены данные"
        )
        
        password = st.text_input(
            "Пароль",
            type="password",
            placeholder="••••••••",
            help="Пароль пользователя БД"
        )
    
    st.markdown("---")
    
    # Таблица всегда перезатирается
    if_exists = 'replace'
    
    # Кнопки управления
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
    
    with col_btn1:
        st.markdown("")  # Отступ
    
    with col_btn2:
        if st.button("Отмена", width="stretch"):
            st.rerun()
    
    with col_btn3:
        export_clicked = st.button("Экспортировать", width="stretch")
    
    # Обработка нажатия кнопки экспорта (вне колонок для полноширинных сообщений)
    if export_clicked:
        # Валидация полей
        errors = []
        
        if not schema or not schema.strip():
            errors.append("Не указана схема базы данных")
        if not table or not table.strip():
            errors.append("Не указано имя таблицы")
        if not user or not user.strip():
            errors.append("Не указан логин пользователя")
        if not password:
            errors.append("Не указан пароль")
        
        if errors:
            for error in errors:
                st.error(f"❌ {error}")
        else:
            # Вызов функции экспорта
            try:
                with st.spinner("Экспорт в базу данных..."):
                    on_export_callback(
                        excel_buffer=excel_buffer,
                        schema=schema.strip(),
                        table=table.strip(),
                        user=user.strip(),
                        password=password,
                        if_exists=if_exists
                    )
                st.success("✅ Данные успешно экспортированы в базу данных!")
            except Exception as e:
                st.error(f"❌ Ошибка при экспорте: {str(e)}")
