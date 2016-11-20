#!/bin/bash

export USER=`whoami`
export BIN="python startapp.py"
export STATUS=`pidof -s ${BIN}`

if [ -z "$STATUS" ]; then
   echo "[`date`] ~/${BIN} is not running";
   nohup python startapp.py &
else
  echo "app running on pid $STATUS"
fi
