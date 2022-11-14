FROM alpine:3.16.1

MAINTAINER R0NAM1 r0nam1@toasty.cafe

RUN apk update && \
    apk add supervisor ffmpeg bash coreutils py3-pip libpq-dev gcc python3-dev musl-dev py3-lxml

RUN rm -rf /var/cache/apk/*

RUN pip3 install requests beautifulsoup4 psycopg2 

COPY ./supervisord.conf /etc/supervisor/supervisord.conf

CMD /usr/bin/supervisord -c /etc/supervisor/supervisord.conf

SHELL ["/bin/bash", "-c"]
