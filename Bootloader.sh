#! /bin/sh
if [ -s upgradeRequest ]; then
        git pull origin
        rm -rf upgradeRequest
fi
if ! [ -s stage_3.txt ]; then
        python3 GearBot/Bot.py
fi
