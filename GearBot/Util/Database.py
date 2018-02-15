import MySQLdb

from Util import configuration


def getConnection():
    return MySQLdb.connect(configuration.getMasterConfigVar("DATABASE_HOST", "localhost"),
                           configuration.getMasterConfigVar("DATABASE_USER", "gearbot"),
                           configuration.getMasterConfigVar("DATABASE_PASS", "password"),
                           configuration.getMasterConfigVar("DATABASE_NAME", "gearbot"),
                           configuration.getMasterConfigVar("DATABASE_PORT", 3306))

def initialize():
    db = getConnection()
    db.close()

def executeStatement(statement, params):
    db = getConnection()
    cursor = db.cursor()
    try:
        cursor.execute(statement, params)
        db.commit()
    except Exception as e:
        cursor.rollback()
        db.close()
        raise e
    db.close()