#!/bin/bash
while true
do

if [[ "$(cat /zemond/fileLock)" == "true" ]]
then

  sleep 4
  export CLIP_NUMBER=$(cat /zemond/video_counter)
  if [[ $(stat --printf="%s" /zemond-storage/out$CLIP_NUMBER.mp4) -ge $CLIP_SIZE ]]
  then
    pkill ffmpeg
  fi

fi

done
