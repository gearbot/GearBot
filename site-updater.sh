#! /bin/sh
cd ~/GearBot/web
npm i > /dev/null
npm run build
rm -rf /var/www/gearbot.rocks/*
cp -a build/* /var/www/gearbot.rocks/
mkdir /var/www/gearbot.rocks/docs
cp -a src/docs/* /var/www/gearbot.rocks/docs