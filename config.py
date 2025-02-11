class Config:
    MYSQL_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': 'password',
        'database': 'xhs'
    }
    
    REDIS_URL = 'redis://localhost:6379/0'
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # 其他配置项...

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False 