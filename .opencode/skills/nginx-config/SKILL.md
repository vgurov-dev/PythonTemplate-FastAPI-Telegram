---
name: nginx-config
description: Nginx reverse proxy configuration - security headers, SSL/TLS, rate limiting, WebSocket, logging
license: MIT
compatibility: opencode
metadata:
  audience: backend-developers, devops
  workflow: infrastructure
---

# Nginx Configuration Skill

## Role

Developer or DevOps working with Nginx as reverse proxy. Covers security headers, SSL/TLS, rate limiting, WebSocket proxy, and proper logging for Loki.

## Project Structure

```
nginx/
├── nginx.conf              # Main config
└── conf.d/
    └── app.conf            # Application routes
```

## Main Configuration

### nginx.conf

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging format for Loki
    log_format loki_json escape=json '{'
        '"time_local":"$time_local",'
        '"remote_addr":"$remote_addr",'
        '"request_uri":"$request_uri",'
        '"status":$status,'
        '"body_bytes_sent":$body_bytes_sent,'
        '"request_time":$request_time,'
        '"http_referer":"$http_referer",'
        '"http_user_agent":"$http_user_agent",'
        '"upstream_addr":"$upstream_addr",'
        '"upstream_status":"$upstream_status"'
    '}';

    access_log /var/log/nginx/access.log loki_json;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    # Security headers (include in all responses)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=general:10m rate=30r/s;
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    # Proxy settings
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_request_buffering off;
    proxy_intercept_errors off;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # WebSocket support
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    include /etc/nginx/conf.d/*.conf;
}
```

## Application Routes

### conf.d/app.conf

```nginx
upstream backend {
    server backend:8000;
    keepalive 32;
}

upstream webapp {
    server webapp:3000;
    keepalive 16;
}

upstream grafana {
    server grafana:3000;
}

server {
    listen 80;
    server_name localhost;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name localhost;

    # SSL Certificate (Let's Encrypt in production)
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_stapling on;
    ssl_stapling_verify on;

    # HSTS (enable after confirming HTTPS works)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # API Backend
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        limit_conn addr 10;

        proxy_pass http://backend/;

        # Increased timeouts for long API calls
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Backend health check (internal)
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }

    # Backend metrics (restricted)
    location /metrics {
        proxy_pass http://backend/metrics;

        # Allow only from internal network
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;

        access_log off;
    }

    # Grafana (external access via /grafana/)
    location /grafana/ {
        proxy_pass http://grafana/;

        # Grafana specific headers
        proxy_set_header Authorization "";

        # Path rewriting for subpath
        rewrite ^/grafana/(.*) /$1 break;
    }

    # WebApp (SPA)
    location / {
        proxy_pass http://webapp;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            proxy_pass http://webapp;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
    }
}
```

## Security Headers

### Detailed Security Headers

```nginx
# X-Frame-Options
# Prevents clickjacking - page can't be embedded in iframe
add_header X-Frame-Options "DENY" always;
# Options: DENY (completely deny), SAMEORIGIN (allow only same origin), ALLOW-FROM uri (specific URI)

# X-Content-Type-Options
# Prevents MIME type sniffing
add_header X-Content-Type-Options "nosniff" always;

# X-XSS-Protection
# Legacy XSS filter (modern browsers have this built-in)
add_header X-XSS-Protection "1; mode=block" always;

# Referrer-Policy
# Controls how much referrer info is sent
add_header Referrer-Policy "no-referrer-when-downgrade" always;
# Options: no-referrer, no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin

# Content-Security-Policy
# Controls what resources can be loaded
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

# Permissions-Policy
# Controls browser features
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

## Rate Limiting

### Global Rate Limiting

```nginx
http {
    # Define rate limit zones
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;      # 10 requests/second per IP
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;       # 1 request/second for login
    limit_req_zone $binary_remote_addr zone=general:10m rate=30r/s;    # 30 requests/second per IP

    # Connection limit zone
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    server {
        # Apply to /api/ endpoints
        location /api/ {
            limit_req zone=api burst=50 nodelay;
            limit_conn addr 10;
            proxy_pass http://backend;
        }

        # Strict limit on auth endpoints
        location /api/auth/login {
            limit_req zone=login burst=5 nodelay;
            proxy_pass http://backend;
        }

        # General pages - looser limit
        location / {
            limit_req zone=general burst=100 nodelay;
            proxy_pass http://webapp;
        }
    }
}
```

### Rate Limiting Response

```nginx
# Custom error page for rate limiting
limit_req_status 429;
limit_conn_status 429;

server {
    error_page 429 = @rate_limit_breached;

    location @rate_limit_breached {
        return 429 '{"error": "rate_limit_exceeded", "retry_after": 60}';
        add_header Content-Type application/json always;
    }
}
```

## WebSocket Proxy

```nginx
server {
    # WebSocket endpoints
    location /ws/ {
        proxy_pass http://backend/ws/;

        # WebSocket headers
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for long-lived connections
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;

        # Disable buffering for WebSocket
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

## SSL/TLS Configuration

### Let's Encrypt (Production)

```nginx
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    # Let's Encrypt certificates
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # Let's Encrypt chain
    ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;

    # Modern TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Session cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
}
```

### Testing SSL Configuration

```bash
# Test SSL certificate
openssl s_client -connect example.com:443 -servername example.com

# Check SSL certificate details
openssl s_client -connect example.com:443 -servername example.com 2>/dev/null | openssl x509 -noout -dates -issuer

# Test with SSL Labs
# https://www.ssllabs.com/ssltest/
```

## Logging for Loki

### Loki JSON Format

```nginx
http {
    log_format loki_json escape=json '{'
        '"time_local":"$time_local",'
        '"remote_addr":"$remote_addr",'
        '"request_uri":"$request_uri",'
        '"status":$status,'
        '"body_bytes_sent":$body_bytes_sent,'
        '"request_time":$request_time,'
        '"http_referer":"$http_referer",'
        '"http_user_agent":"$http_user_agent"'
    '}';

    access_log /var/log/nginx/access.log loki_json;
}
```

### Grafana Loki Query Examples

```loki
# All 5xx errors
{job="nginx"} |= "status" | json | status >= 500

# Slow requests (>1s)
{job="nginx"} | json | request_time > 1

# Specific endpoint
{job="nginx"} |= "/api/users"

# IP whitelist violations
{job="nginx"} | json | remote_addr != "10.0.0.0/8"

# User agent analysis
{job="nginx"} | json | http_user_agent =~ "(?i)(curl|wget|python)"
```

## Docker Configuration

```yaml
# docker-compose.staging.yml
services:
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - webapp
      - grafana
    logging:
      driver: loki
      options:
        loki-url: "http://loki:3100/loki/api/v1/push"
        loki-retries: "3"
        loki-batch-size: "400"
    networks:
      - app-network
```

## Common Patterns

### Redirect HTTP to HTTPS

```nginx
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

### Path Rewriting

```nginx
# /api/v1 -> /api/
location ~ ^/api/v[0-9]+ {
    rewrite ^/api/v[0-9]+(.*) $1 break;
    proxy_pass http://backend;
}

# Remove trailing slash
location ~ (?<;!)/$ {
    rewrite ^(.+)/$ $1 permanent;
}
```

### Load Balancing

```nginx
upstream backend {
    least_conn;  # Least connections algorithm

    server backend1:8000 weight=5;
    server backend2:8000 weight=3;
    server backend3:8000 weight=2 backup;  # Backup
}

server {
    location /api/ {
        proxy_pass http://backend;
    }
}
```

## Anti-Patterns (NEVER do)

| Anti-pattern | Problem | Solution |
|-------------|---------|----------|
| `allow_origins: *` | CORS wide open | Whitelist specific origins |
| No SSL on public endpoints | Data in plain text | Enable HTTPS |
| `/metrics` public | Internal data leak | Restrict to internal IPs |
| No rate limiting | DoS vulnerability | Add rate limits |
| Missing security headers | Vulnerable to attacks | Add all security headers |
| Long timeouts everywhere | Resource exhaustion | Set appropriate timeouts |
| `proxy_pass` without trailing slash | Path mismatch | Be explicit about paths |
| No logging | No visibility | Enable Loki JSON logging |

## Testing Configuration

```bash
# Test nginx configuration
nginx -t

# Reload without downtime
nginx -s reload

# Full restart
docker compose restart nginx
```

## Checklist

Before deploying Nginx:

- [ ] `nginx -t` passes without errors
- [ ] All endpoints have appropriate rate limits
- [ ] `/metrics` restricted to internal access
- [ ] Security headers present
- [ ] SSL configured (even for internal)
- [ ] Logging to Loki configured
- [ ] Timeouts appropriate for endpoints
- [ ] No `allow_origins: *` in CORS
- [ ] Health check configured
