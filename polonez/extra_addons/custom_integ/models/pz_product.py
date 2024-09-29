import pyodbc
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

# Настройка логирования
_logger = logging.getLogger(__name__)


class PzProductBarcodeHistory(models.Model):
    _name = 'pz.product.barcode.history'
    _description = 'Product Barcode Change History'
    _rec_name = 'barcode'

    product_id = fields.Many2one('pz.product', string="Product", required=True, ondelete='cascade')
    barcode = fields.Char(string="Barcode", required=True, index=True)
    change_date = fields.Datetime(string="Change Date", default=fields.Datetime.now, required=True)


class PzProduct(models.Model):
    _name = 'pz.product'
    _description = 'External Product Integration'

    name = fields.Char(string="External Product Name", required=True)
    external_id = fields.Integer(string="External Product ID", index=True, required=True, unique=True)
    barcode = fields.Char(string="Barcode", index=True)
    price = fields.Float(string="Price")  # Добавлено поле для цены
    product_id = fields.Many2one('product.template', string="Related Product", ondelete='cascade')
    barcode_history_ids = fields.One2many('pz.product.barcode.history', 'product_id', string="Barcode History")

    @api.model
    def import_products_from_mssql(self):
        """
        Метод импорта данных из MSSQL в Odoo, включающий обработку eventual consistency,
        логирование, и интеграцию дополнительных атрибутов продукта.
        """
        try:
            # Подключение к MSSQL Server
            conn = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL Server};'
                'SERVER=your_server_name;'  # Замените на имя вашего сервера
                'DATABASE=your_database_name;'  # Замените на название вашей базы данных
                'UID=your_username;'  # Замените на ваше имя пользователя
                'PWD=your_password'  # Замените на ваш пароль
            )
            cursor = conn.cursor()
            _logger.info("Successfully connected to MSSQL Server")

            # Выполнение запроса для получения данных из таблицы Products
            cursor.execute("SELECT ProductID, ProductName, Price FROM dbo.Products")
            products = cursor.fetchall()
            _logger.info("Fetched %s products from MSSQL", len(products))

            # Выполнение запроса для получения данных из таблицы ProductBarcodes
            cursor.execute("SELECT ProductID, Barcode FROM logistics.ProductBarcodes")
            barcodes = cursor.fetchall()
            _logger.info("Fetched %s barcodes from MSSQL", len(barcodes))

            # Сопоставление товаров с баркодами
            barcode_map = {row.ProductID: row.Barcode for row in barcodes}

            # Импорт данных в Odoo
            for product in products:
                product_id = product.ProductID
                product_name = product.ProductName
                price = product.Price
                barcode = barcode_map.get(product_id, '')

                # Проверяем, существует ли продукт уже в Odoo по external_id
                existing_product = self.search([('external_id', '=', product_id)], limit=1)

                if existing_product:
                    # Проверяем, изменился ли баркод или цена
                    if existing_product.barcode != barcode or existing_product.price != price:
                        # Проверка на наличие дублирующегося баркода
                        duplicate_product = self.search([('barcode', '=', barcode)], limit=1)
                        if duplicate_product and duplicate_product.id != existing_product.id:
                            _logger.warning("Barcode conflict detected: Product with external_id %s has a duplicate barcode %s already used by another product with ID %s.", product_id, barcode, duplicate_product.id)

                        # Добавляем запись об изменении баркода в историю
                        if existing_product.barcode != barcode:
                            self.env['pz.product.barcode.history'].create({
                                'product_id': existing_product.id,
                                'barcode': existing_product.barcode,
                                'change_date': fields.Datetime.now(),
                            })

                        # Обновляем продукт
                        existing_product.write({
                            'name': product_name,
                            'barcode': barcode,
                            'price': price,  # Обновляем цену
                        })
                        _logger.info("Updated product with external_id %s", product_id)
                else:
                    # Проверка на наличие дублирующегося баркода
                    duplicate_product = self.search([('barcode', '=', barcode)], limit=1)
                    if duplicate_product:
                        _logger.warning("Barcode conflict detected: New product with external_id %s has a duplicate barcode %s already used by another product with ID %s.", product_id, barcode, duplicate_product.id)

                    # Создаем новый продукт в product.template
                    product_template = self.env['product.template'].create({
                        'name': product_name,
                        'barcode': barcode,
                        'list_price': price,  # Присваиваем цену в стандартной модели Odoo
                    })

                    # Создаем запись в кастомной модели pz.product
                    new_product = self.create({
                        'external_id': product_id,
                        'name': product_name,
                        'barcode': barcode,
                        'price': price,  # Сохраняем цену
                        'product_id': product_template.id
                    })

                    # Сохраняем запись в историю изменений баркодов
                    self.env['pz.product.barcode.history'].create({
                        'product_id': new_product.id,
                        'barcode': barcode,
                        'change_date': fields.Datetime.now(),
                    })
                    _logger.info("Created new product with external_id %s", product_id)

            # Закрываем соединение с базой данных
            cursor.close()
            conn.close()
            _logger.info("Data import from MSSQL completed successfully")

        except pyodbc.Error as e:
            error_message = _("Error connecting to MSSQL Server: %s" % e)
            _logger.error(error_message)
            raise UserError(error_message)
        except Exception as e:
            error_message = _("Unexpected error occurred during data import: %s" % e)
            _logger.error(error_message)
            raise UserError(error_message)
