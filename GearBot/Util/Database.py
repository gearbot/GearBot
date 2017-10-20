import logging

import MySQLdb

from Util import configuration


def getConnection():
    return MySQLdb.connect(configuration.getConfigVar("DATABASE_HOST", "localhost"),
                           configuration.getConfigVar("DATABASE_USER", "gearbot"),
                           configuration.getConfigVar("DATABASE_PASS", "password"),
                           configuration.getConfigVar("DATABASE_NAME", "gearbot"),
                           configuration.getConfigVar("DATABASE_PORT", 3306))

def initialize():
    db = getConnection()
    cursor = db.cursor()
    ensureTableExists(cursor, "command",
                      "create table command(name varchar(50) not null,	text text not null,	server varchar(25) not null, primary key (name, server));")
    db.close()

def ensureTableExists(cursor, tablename, creator):
    cursor.execute(f"""
          SELECT COUNT(*)
          FROM information_schema.tables
          WHERE table_name = '{tablename}'
          """)
    if cursor.fetchone()[0] == 0:
        logging.warning(f"Table {tablename} did not exist and had to be created")
        cursor.execute(creator)

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