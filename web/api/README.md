# Gearbot Web API Backend

### Info
In order to properly use this, you will need to generate burner permissions for guilds you are in.

The structure should be as so:

```python
gearbotPermsData = {
    YourUserIDHereAsAnInteger: {
        GUILDIDHERE: 9101,
        GUILDIDHERE: 9000,
        etc
    }
}
```

Refer to `AuthValue Schema.txt` for what the auth value bitmasks mean.