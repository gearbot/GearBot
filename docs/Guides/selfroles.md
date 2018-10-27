# **What are selfroles?**
Selfroles are roles that can be self-assigned by a user by using the `!role` command. The `!role` command can be used by everyone by default (The permission level is 0), so only make roles selfroles if you want anyone to be able to add the role to themselves.
Selfroles can be useful for roles such as:
 - Pingable announcement roles
 - Language roles
 - Giveaway participator roles
 - etc.
# **How do I add selfroles?**
To add or remove selfroles, you'll need a permission level of 3 by default (Administrator permission or Adminstrator role). To add a selfrole, use this command (Mention not recommended).
```
!configure self_role add <role-name/id/mention>
```
Once you've done this, users will can add the role to themselves by using the `!role` command.
To remove a selfrole, use this command instead.
```
!configure self_role remove <role-name/id/mention>
```
# **How do I use selfroles?**
To display a list of the server's selfroles, use the `!role` command.
```
!role
```

To add or remove a selfrole to yourself, use the `!role` command with the role name/id/mention(not recommended) argument.
```
!role <role-name/id/mention>
```
Do not confuse the `!role` command with `!roles` command, that shows all the server's roles instead.
