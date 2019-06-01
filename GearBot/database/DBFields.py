from peewee import IntegerField

class TinyIntField(IntegerField):
    field_type = 'TINYINT'
