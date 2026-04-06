From nginx:1.29.5

COPY configs/proxy.conf /etc/nginx/conf.d/

ENTRYPOINT /usr/sbin/nginx -g 'daemon off;' -c /etc/nginx/nginx.conf