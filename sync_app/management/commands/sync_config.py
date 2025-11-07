# sync_app/management/commands/sync_config.py
SYNC_CONFIG = {
    # تنظیمات عمومی
    'settings': {
        'sync_intervals': {
            'quick': 300,  # 5 دقیقه برای داده‌های مهم
            'normal': 600,  # 10 دقیقه
            'slow': 1800,  # 30 دقیقه برای داده‌های کم اهمیت
        },
        'retry_policy': {
            'max_retries': 3,
            'backoff_factor': 2,
        },
        'batch_sizes': {
            'small': 50,
            'medium': 100,
            'large': 200
        }
    },

    # پیکربندی مدل‌ها
    'models': {
        'auth': {
            'User': {
                'fields': ['username', 'first_name', 'last_name', 'email', 'is_active', 'date_joined', 'last_login'],
                'batch_size': 100,
                'sync_priority': 'high',
                'exclude_fields': ['password', 'groups', 'user_permissions']
            }
        },
        'account_app': {
            'Product': {
                'fields': ['name', 'description', 'price', 'category', 'stock_quantity', 'barcode', 'created_at'],
                'batch_size': 100,
                'sync_priority': 'high'
            },
            'Customer': {
                'fields': ['name', 'phone', 'email', 'address', 'created_at'],
                'batch_size': 100,
                'sync_priority': 'high'
            },
            'Expense': {
                'fields': ['title', 'amount', 'category', 'description', 'date', 'branch_id', 'user_id'],
                'batch_size': 50,
                'sync_priority': 'medium'
            },
            'InventoryCount': {
                'fields': ['product_name', 'quantity', 'count_date', 'branch_id', 'selling_price'],
                'batch_size': 50,
                'sync_priority': 'high'
            },
            'StockTransaction': {
                'fields': ['product_id', 'quantity', 'transaction_type', 'notes', 'created_at'],
                'batch_size': 100,
                'sync_priority': 'medium'
            }
        },
        'cantact_app': {
            'Branch': {
                'fields': ['name', 'address', 'phone', 'is_active', 'created_at'],
                'batch_size': 50,
                'sync_priority': 'high'
            },
            'accuntmodel': {
                'fields': ['name', 'phone', 'email', 'address'],
                'batch_size': 100,
                'sync_priority': 'medium'
            },
            'savecodphon': {
                'fields': ['code', 'phone', 'is_used', 'created_at'],
                'batch_size': 100,
                'sync_priority': 'low'
            },
            'phonnambermodel': {
                'fields': ['number', 'type', 'is_active'],
                'batch_size': 100,
                'sync_priority': 'medium'
            }
        },
        'invoice_app': {
            'Invoicefrosh': {
                'fields': ['customer_name', 'customer_phone', 'total_amount', 'payment_method', 'is_paid',
                           'created_at'],
                'batch_size': 50,
                'sync_priority': 'high'
            },
            'InvoiceItemfrosh': {
                'fields': ['invoice_id', 'product_id', 'quantity', 'price', 'total_price'],
                'batch_size': 100,
                'sync_priority': 'high'
            },
            'POSTransaction': {
                'fields': ['transaction_id', 'amount', 'status', 'created_at'],
                'batch_size': 100,
                'sync_priority': 'medium'
            }
        },
        'dashbord_app': {
            'Invoice': {
                'fields': ['invoice_number', 'customer_name', 'total_amount', 'date', 'status'],
                'batch_size': 50,
                'sync_priority': 'high'
            },
            'Froshande': {
                'fields': ['name', 'phone', 'company', 'is_active'],
                'batch_size': 100,
                'sync_priority': 'medium'
            }
        },
        'pos_payment': {
            'POSTransaction': {
                'fields': ['transaction_id', 'amount', 'payment_method', 'status', 'created_at'],
                'batch_size': 100,
                'sync_priority': 'medium'
            }
        }
    }
}

# برای سازگاری با کدهای موجود
SYNC_SETTINGS = SYNC_CONFIG['settings']