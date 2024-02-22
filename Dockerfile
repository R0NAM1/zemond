FROM debian:trixie

MAINTAINER R0NAM1 r0nam1@toasty.cafe

RUN apt update && \
    apt install supervisor tzdata ffmpeg bash coreutils python3 python3-pip libpq-dev gcc python3-dev musl-dev python3-lxml python3-psycopg2 python3-bs4 python3-requests python3-m3u8 python3-av -y
    
RUN apt clean

COPY ./supervisord.conf /etc/supervisor/supervisord.conf

CMD /usr/bin/supervisord -c /etc/supervisor/supervisord.conf

SHELL ["/bin/bash", "-c"]
