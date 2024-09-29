
# Интеграция Odoo с внешней учетной системой

Этот проект представляет собой сервис односторонней интеграции, который синхронизирует данные о продуктах из внешней учетной системы (на базе MS Access и MS SQL Server) в Odoo. Интеграция обновляет справочник товаров в Odoo, обеспечивая согласованность данных с внешней системой и включает механизмы обработки потенциальных конфликтов, таких как дублирующиеся штрихкоды.

## Содержание
- [Описание](#описание)
- [Основные возможности](#основные-возможности)
- [Установка](#установка)
- [Настройка](#настройка)
- [Использование](#использование)
- [Обработка конфликтов штрихкодов](#обработка-конфликтов-штрихкодов)
- [Логирование и обработка ошибок](#логирование-и-обработка-ошибок)
- [Настройка Cron](#настройка-cron)
- [Лицензия](#лицензия)

## Описание

Внешняя учетная система хранит данные о продуктах, штрихкодах, ценах и других складских операциях. Данная интеграция синхронизирует ключевые данные продуктов (ID продукта, название, штрихкод и цена) из внешней системы в Odoo.

Интеграция является **односторонней** — данные передаются только из внешней системы в Odoo, без обратной синхронизации.

## Основные возможности

- **Синхронизация продуктов:** Импорт данных о продуктах из внешней системы в Odoo.
- **Eventual Consistency:** Обработка eventual consistency в присвоении штрихкодов, учитывая временные дублирующиеся штрихкоды.
- **История изменения штрихкодов:** Логирование изменений штрихкодов в отдельной модели.
- **Синхронизация цен:** Обновление цен на продукты в Odoo при изменении в внешней системе.
- **Обнаружение конфликтов:** Выявление и логирование конфликтов штрихкодов в процессе синхронизации.
- **Автоматический импорт:** Поддержка автоматического импорта через Cron задачу.

## Установка

1. **Клонирование репозитория:**
   ```bash
   git clone https://github.com/AntonBalmakov/Polonez-Integration
   ```

2. **Установка необходимых Python-библиотек:**
   Убедитесь, что установлена библиотека `pyodbc`, которая используется для взаимодействия с MS SQL Server:
   ```bash
   pip install pyodbc
   pip install -r requirements.txt
   ```

3. **Убедитесь, что локально установлена Odoo 13:**
   Для работы интеграции требуется установленная локально версия Odoo 13. Вы можете следовать [официальной документации по установке Odoo 13](https://www.odoo.com/documentation/13.0/ru/).

4. **Установка модуля Odoo:**
   - Скопируйте папку модуля в директорию с пользовательскими модулями Odoo (`custom addons`).
   - Обновите список приложений в Odoo и установите модуль через интерфейс Odoo.

5. **Настройка ODBC:**
   Убедитесь, что на сервере, где работает Odoo, установлен правильный ODBC-драйвер. Интеграция использует `ODBC Driver 17 for SQL Server` для подключения к MS SQL Server.

6. **Настройка соединения с базой данных:**
   Обновите параметры подключения к базе данных внешней учетной системы в методе `import_products_from_mssql`:
   ```python
   conn = pyodbc.connect(
       'DRIVER={ODBC Driver 17 for SQL Server};'
       'SERVER=your_server_name;'  # Имя сервера MS SQL
       'DATABASE=your_database_name;'  # Имя базы данных
       'UID=your_username;'  # Имя пользователя
       'PWD=your_password;'  # Пароль
   )
   ```

## Настройка

1. **Настройка соединения с MS SQL:**
   В методе `import_products_from_mssql` необходимо заменить параметры соединения с MS SQL Server на ваши данные.

2. **Конфигурация моделей Odoo:**
   Модуль расширяет стандартную модель продуктов в Odoo и создает кастомную модель `pz.product`, которая управляет импортированными продуктами из внешней системы.

3. **Настройка Cron-задачи:**
   В файле данных XML предусмотрена автоматическая задача для регулярного импорта данных из внешней системы:
   ```xml
   <odoo>
       <record id="ir_cron_import_products_from_mssql" model="ir.cron">
           <field name="name">Импорт продуктов из MSSQL</field>
           <field name="model_id" ref="model_pz_product"/>
           <field name="state">code</field>
           <field name="code">model.import_products_from_mssql()</field>
           <field name="interval_number">1</field>
           <field name="interval_type">hours</field>
           <field name="numbercall">-1</field>
           <field name="active">True</field>
       </record>
   </odoo>
   ```

4. **Конфигурация Odoo для работы с внешними продуктами:**
   В настройках Odoo добавлены модели `pz.product` для хранения информации о продуктах, синхронизируемых с внешней системой. 

## Использование

1. После настройки модуля и Cron-задачи, импорт продуктов происходит автоматически в установленный интервал времени (по умолчанию — каждый час).
2. Все импортированные продукты будут отображаться в справочнике Odoo, где они будут сопоставляться с соответствующими продуктами по внешнему идентификатору.

## Обработка конфликтов штрихкодов

Интеграция обрабатывает случаи временного дублирования штрихкодов в рамках eventual consistency. Если во внешней системе временно два или более продукта имеют один и тот же штрихкод, система Odoo:
- Логирует предупреждение в журнале о конфликте.
- При необходимости сохраняет историю изменений штрихкодов в модели `pz.product.barcode.history`.
- В случае конфликта обновления баркода в Odoo будет сохраняться информация о предыдущем штрихкоде.

## Логирование и обработка ошибок

Логирование осуществляется с использованием стандартного механизма Odoo и Python. В случае ошибки при подключении к базе данных MSSQL или при возникновении других проблем, интеграция:
- Записывает информацию об ошибке в журнал.
- В случае критических ошибок выбрасывает исключение `UserError`, которое останавливает выполнение задачи импорта.

Пример обработки ошибки:
```python
except pyodbc.Error as e:
    error_message = _("Ошибка подключения к MSSQL Server: %s" % e)
    _logger.error(error_message)
    raise UserError(error_message)
except Exception as e:
    error_message = _("Неожиданная ошибка во время импорта: %s" % e)
    _logger.error(error_message)
    raise UserError(error_message)
```

## Настройка Cron

Для автоматического импорта данных из внешней системы используется Cron-задача. Она настроена для выполнения каждый час, но вы можете изменить интервал в настройках Odoo.

## Лицензия

Этот проект доступен под лицензией MIT. Подробности можно найти в файле `LICENSE`.