import logging

import MySQLdb

import Variables


def getConnection():
    return MySQLdb.connect("localhost", Variables.CONFIG_SETTINGS["DATABASE_USER"], Variables.CONFIG_SETTINGS["DATABASE_PASS"], Variables.CONFIG_SETTINGS["DATABASE_NAME"])

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