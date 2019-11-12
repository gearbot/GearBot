from tortoise import Model
from tortoise.fields import IntField, BigIntField, CharField, BooleanField, DatetimeField


class InfractionMigration(Model):
    id = IntField(pk=True)
    guild_id = BigIntField()
    user_id = BigIntField()
    mod_id = BigIntField()
    type = CharField(max_length=10, collation="utf8mb4_general_ci")
    reason = CharField(max_length=2000, collation="utf8mb4_general_ci")
    start = IntField()
    end = BigIntField(null=True)
    active = BooleanField(default=True)

    class Meta:
        table = "infraction"
        
        
class Infraction(Model):
    id = IntField(pk=True)
    guild_id = BigIntField()
    user_id = BigIntField()
    mod_id = BigIntField()
    type = CharField(max_length=10, collation="utf8mb4_general_ci")
    reason = CharField(max_length=2000, collation="utf8mb4_general_ci")
    start = DatetimeField()
    end = DatetimeField(null=True)
    active = BooleanField(default=True)

    class Meta:
        table = "infraction"