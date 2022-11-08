#!/bin/bash
while true
do

if [[ $(cat /zemond/fileLock-$CAMERA_NAME) == "true" ]]
then

  export CLIP_NUMBER=$(cat /zemond/video_counter-$CAMERA_NAME)
  if [[ $(stat --printf="%s" /zemond-temp/$CAMERA_NAME-$CLIP_NUMBER.mp4) -ge $CLIP_SIZE ]]
  then
    pkill ffmpeg
    mv -f /zemond-temp/$CAMERA_NAME-$CLIP_NUMBER.mp4 /zemond-storage/$CAMERA_NAME/$CAMERA_NAME-$CLIP_NUMBER.mp4
    mv -f /zemond-temp/$CAMERA_NAME-$CLIP_NUMBER.starttime /zemond-storage/$CAMERA_NAME/$CAMERA_NAME-$CLIP_NUMBER.starttime
    mv -f /zemond-temp/$CAMERA_NAME-$CLIP_NUMBER.endtime /zemond-storage/$CAMERA_NAME/$CAMERA_NAME-$CLIP_NUMBER.endtime
    sleep 10
  fi

fi

done
