FROM alpine:3.15

MAINTAINER R0NAM1 r0nam1@toasty.cafe

RUN apk update && \
    apk add supervisor ffmpeg bash coreutils

RUN rm -rf /var/cache/apk/*

COPY ./supervisord.conf /etc/supervisor/supervisord.conf

CMD /usr/bin/supervisord -c /etc/supervisor/supervisord.conf

SHELL ["/bin/bash", "-c"]
