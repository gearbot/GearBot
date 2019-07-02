@echo off

IF EXIST upgradeRequest (
  git pull origin
  py -3 -m pip install -U -r requirements.txt --user
  del upgradeRequest
)
IF NOT EXIST stage_3.txt (
  py -3 GearBot/GearBot.py
)
