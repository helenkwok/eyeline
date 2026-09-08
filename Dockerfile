FROM nginx:alpine

# Default Cloud Run PORT
ENV PORT=8080

# Configure Nginx template for automated envsubst
COPY deploy/nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy UI review station and judge portal
COPY ui/ /usr/share/nginx/html/

# Copy Benchmark dataset, fixtures, and rendered MP4 video clips
COPY bench/truth.json /usr/share/nginx/html/bench/truth.json
COPY bench/fixtures/ /usr/share/nginx/html/bench/fixtures/
COPY bench/clips/ /usr/share/nginx/html/bench/clips/

# Copy state receipt for fresh inspection
COPY docs/STATE.md /usr/share/nginx/html/STATE.md

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -q -O - http://localhost:${PORT}/ || exit 1
