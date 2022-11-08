while true
do

export CLIP_NUMBER=$(cat /zemond/video_counter-$CAMERA_NAME)

mkdir /zemond-storage/$CAMERA_NAME

export CLIP_NUMBER=$(expr $(echo $CLIP_NUMBER) + 1) 
echo $CLIP_NUMBER > /zemond/video_counter-$CAMERA_NAME

if [[ $(cat /zemond/video_counter-$CAMERA_NAME) -ge $(expr $(echo $CLIP_LIMIT) + 1) ]]
        then
                echo 1 > /zemond/video_counter-$CAMERA_NAME
                export CLIP_NUMBER=$(cat /zemond/video_counter-$CAMERA_NAME)
fi

echo true > /zemond/fileLock-$CAMERA_NAME

echo $(date +%s) > /zemond-temp/$CAMERA_NAME-$CLIP_NUMBER.starttime

ffmpeg  \
        -rtsp_transport tcp \
        -re \
        -i $RTSP_PATHS_CAM1_SOURCE \
        -acodec copy \
        -vcodec copy \
        -movflags frag_keyframe \
        -y /zemond-temp/$CAMERA_NAME-$CLIP_NUMBER.mp4
#        -vcodec copy -f hls -hls_time 1 -hls_flags delete_segments /publicHTML/$CAMERA_NAME.m3u8
#        -vf setpts=0 -fflags nobuffer -rtsp_flags listen -codec copy -f rtsp -rtsp_transport tcp rtsp://localhost:8554/mystream \

#-hls_playlist_type event

echo $(date +%s) > /zemond-temp/$CAMERA_NAME-$CLIP_NUMBER.endtime

echo false > /zemond/fileLock-$CAMERA_NAME

done

