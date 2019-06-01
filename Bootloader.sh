#! /bin/sh
if [ -s upgradeRequest ]; then
        git pull origin
        python3 -m pip install -U -r requirements.txt
        rm -rf upgradeRequest
fi
if ! [ -s stage_3.txt ]; then
        python3 GearBot/GearBot.py
fi
