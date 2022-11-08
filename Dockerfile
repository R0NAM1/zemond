FROM alpine:3.16.1

MAINTAINER R0NAM1 r0nam1@toasty.cafe

RUN apk update && \
    apk add supervisor ffmpeg bash coreutils npm

RUN rm -rf /var/cache/apk/*

RUN npm install -g http-server

COPY ./supervisord.conf /etc/supervisor/supervisord.conf

CMD /usr/bin/supervisord -c /etc/supervisor/supervisord.conf

SHELL ["/bin/bash", "-c"]
