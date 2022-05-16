while true
do

export CLIP_NUMBER=$(cat /zemond/video_counter)

export CLIP_NUMBER=$(expr $(echo $CLIP_NUMBER) + 1) 
echo $CLIP_NUMBER > /zemond/video_counter

if [[ $(cat /zemond/video_counter) -ge $CLIP_LIMIT ]]
        then
                echo 1 > /zemond/video_counter
                export CLIP_NUMBER=$(cat /zemond/video_counter)
fi

echo true > /zemond/fileLock

ffmpeg  \
        -rtsp_transport tcp \
        -re \
        -i $CAMERA_URL \
        -acodec copy \
        -vcodec copy -y /zemond-storage/out$CLIP_NUMBER.mp4 \
        -vcodec copy -f rtsp -rtsp_transport tcp rtsp://localhost:8554/mystream

echo false > /zemond/fileLock

echo "Killing FFMPEG at $(stat --printf="%s" /zemond-storage/out$CLIP_NUMBER.mp4)"

done

