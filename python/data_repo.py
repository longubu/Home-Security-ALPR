'''Helper functions for MySQL database processes
'''
import mysql.connector
import os
from models import LicensePlateData


def db_upsert(data: LicensePlateData):
    '''Insert license plate event to databases'''
    # login
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password=os.getenv("MYSQL_PASS"),
            database="database"
        )
        
        # check if license plate already seen 
        query_result = query(mydb, data.text)
        if query_result is None:
            # else add new license plate to license database
            insert_license_plate(mydb, data)
            
        # record new event to camera events database
        increment_seen(mydb, data.text)
        mydb.commit()
    except NameError:
        print("Error Writing to Database")


def insert_license_plate(db, data: LicensePlateData):
    '''Insert new license plate into license database'''
    cursor = db.cursor()
    sql = "INSERT INTO license_plates (license_plate) VALUES (%s)"
    val = (data.text,)
    cursor.execute(sql, val)


def increment_seen(db, plate: str):
    '''Increment license plate events to camera events database'''
    cursor = db.cursor()
    sql = "INSERT INTO camera_events (license_plate) VALUES (%s)"
    val = (plate,)
    cursor.execute(sql, val)


def query(db, param):
    '''Check if license plate is already in license database'''
    cursor = db.cursor()
    sql = "SELECT * FROM license_plates where license_plate = %s"
    adr = (param,)
    cursor.execute(sql, adr)
    return cursor.fetchone()