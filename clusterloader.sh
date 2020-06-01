#! /bin/bash
if [ -s upgradeRequest ]; then
        git pull origin
        python3 -m pip install -U -r requirements.txt --user
        rm -rf upgradeRequest
fi
SHARDS=2
CLUSTERS=2
COUNT=0
TOTAL_SHARDS=$(($SHARDS * $CLUSTERS))
LAST=$(($SHARDS-1))
while [[ $COUNT < $LAST ]]; do
  OFFSET=$((SHARDS*$COUNT))
  echo "Starting GearBot cluster $COUNT with $SHARDS shards (offset $OFFSET)"
  $(python3 GearBot/GearBot.py --total_shards $TOTAL_SHARDS --num_shards $SHARDS --offset $OFFSET &)
  sleep $((5*$SHARDS))
  COUNT=$(($COUNT+1))
done
$(python3 GearBot/GearBot.py --total_shards $TOTAL_SHARDS --num_shards $SHARDS --offset $OFFSET)