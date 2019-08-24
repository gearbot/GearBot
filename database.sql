create table customcommand
(
    id       int unsigned auto_increment primary key,
    serverid bigint        not null,
    trigger  varchar(20)   not null,
    response varchar(2000) not null,
    index (serverid)
);

create table user
(
    userid        bigint primary key not null,
    name          varchar(32)        not null,
    discriminator smallint           not null
);


create table loggedmessage
(
    messageid bigint primary key                       not null,
    content   varchar(2000) collate utf8mb4_general_ci null,
    author    bigint                                   not null,
    channel   bigint                                   not null,
    server    bigint                                   not null,
    type      tinyint                                  null,
    pinnned   bool,
    index (author),
    index (channel),
    index (server)

);

create table loggedattachment
(
    id        bigint primary key not null,
    name      varchar(100)       not null,
    isImage   bool               not null,
    messageid bigint references loggedmessage (messageid),
    index (messageid)
);

create table infraction
(
    id       int unsigned primary key not null,
    guild_id bigint                   not null,
    user_id  bigint                   not null,
    mod_id   bigint                   not null,
    type     varchar(10)              not null
);


create table reminder
(
    id         int unsigned primary key not null,
    user_id    bigint                   not null,
    channel_id bigint                   not null,
    guild_id   bigint                   not null,
    message_id bigint                   not null,
    dm         tinyint(1),
    to_remind  varchar(1800) collate utf8mb4_general_ci,
    send       int unsigned             not null,
    time       int unsigned             not null,
    status     enum ('1', '2', '3'),
    index (user_id)
);

create table dashsession
(
    token varchar(50) primary key not null,
    user_id bigint not null,
    api_token varchar(100) not null,
    refresh_token varchar(100) not null,
    expires_at datetime not null,
    index(user_id)
)

