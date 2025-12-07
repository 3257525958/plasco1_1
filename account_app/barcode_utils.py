# account_app/barcode_utils.py
import barcode
from barcode.writer import ImageWriter
import base64
from io import BytesIO
import qrcode


class BarcodeGenerator:
    """کلاس تولید بارکدهای معتبر"""

    @staticmethod
    def generate_code128(barcode_data, width=400, height=100):
        """تولید بارکد Code128"""
        try:
            # پاکسازی داده بارکد
            barcode_str = str(barcode_data).strip()

            # حذف کاراکترهای غیرمجاز
            import re
            barcode_str = re.sub(r'[^0-9a-zA-Z]', '', barcode_str)

            if not barcode_str:
                raise ValueError("داده بارکد خالی است")

            # تنظیمات writer
            writer = ImageWriter()
            writer.set_options({
                'module_height': 15.0,
                'module_width': 0.3,
                'font_size': 0,  # غیرفعال کردن متن
                'quiet_zone': 6.5,
                'background': 'white',
                'foreground': 'black',
                'write_text': False,  # نمایش متن غیرفعال
                'dpi': 300,
            })

            # تولید بارکد Code128
            code128 = barcode.get_barcode_class('code128')
            barcode_obj = code128(barcode_str, writer=writer)

            # ذخیره در buffer
            buffer = BytesIO()
            barcode_obj.write(buffer)
            buffer.seek(0)

            # تبدیل به base64
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            print(f"خطا در تولید Code128: {e}")
            return None

    @staticmethod
    def generate_ean13(barcode_data):
        """تولید بارکد EAN-13 (13 رقمی)"""
        try:
            barcode_str = str(barcode_data).strip()
            barcode_str = ''.join(c for c in barcode_str if c.isdigit())

            # EAN-13 باید 13 رقمی باشد
            if len(barcode_str) < 13:
                # اضافه کردن صفر از چپ
                barcode_str = barcode_str.zfill(13)
            elif len(barcode_str) > 13:
                barcode_str = barcode_str[:13]

            # تولید بارکد
            writer = ImageWriter()
            writer.set_options({
                'module_height': 15.0,
                'module_width': 0.33,
                'font_size': 10,
                'quiet_zone': 6.5,
                'background': 'white',
                'foreground': 'black',
                'write_text': False,
            })

            ean13 = barcode.get_barcode_class('ean13')
            barcode_obj = ean13(barcode_str, writer=writer)

            buffer = BytesIO()
            barcode_obj.write(buffer)
            buffer.seek(0)

            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            print(f"خطا در تولید EAN-13: {e}")
            return None

    @staticmethod
    def generate_upc_a(barcode_data):
        """تولید بارکد UPC-A (12 رقمی)"""
        try:
            barcode_str = str(barcode_data).strip()
            barcode_str = ''.join(c for c in barcode_str if c.isdigit())

            # UPC-A باید 12 رقمی باشد
            if len(barcode_str) < 12:
                barcode_str = barcode_str.zfill(12)
            elif len(barcode_str) > 12:
                barcode_str = barcode_str[:12]

            writer = ImageWriter()
            writer.set_options({
                'module_height': 15.0,
                'module_width': 0.33,
                'font_size': 10,
                'quiet_zone': 6.5,
                'background': 'white',
                'foreground': 'black',
                'write_text': False,
            })

            upca = barcode.get_barcode_class('upc')
            barcode_obj = upca(barcode_str, writer=writer)

            buffer = BytesIO()
            barcode_obj.write(buffer)
            buffer.seek(0)

            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            print(f"خطا در تولید UPC-A: {e}")
            return None

    @staticmethod
    def get_barcode_type(barcode_str):
        """تشخیص نوع بارکد بر اساس طول"""
        barcode_str = str(barcode_str).strip()
        digits = ''.join(c for c in barcode_str if c.isdigit())

        length = len(digits)

        if length == 12:
            return 'upca'
        elif length == 13:
            return 'ean13'
        elif length <= 128:  # Code128 می‌تواند تا 128 کاراکتر باشد
            return 'code128'
        else:
            return 'code128'  # پیش‌فرض