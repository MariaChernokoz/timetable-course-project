import os
from dotenv import load_dotenv

load_dotenv()

import os
from dotenv import load_dotenv

load_dotenv()

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or '336c8e1b3598c552b1b672b42e1271d04357c3a09d550eb83c609b512acc875b'
    POSTGRES_USER = os.environ.get('POSTGRES_USER') or 'postgres'
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD') or '60ayc4ljgCvrYBms'
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST') or 'closely-original-tomcat.data-1.euc1.tembo.io'
    POSTGRES_PORT = os.environ.get('POSTGRES_PORT') or '5432'
    POSTGRES_DB = os.environ.get('POSTGRES_DB') or 'postgres'