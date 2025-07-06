# Traefik to Pangolin Sync

Synchronizes HTTP routes from multiple Traefik instances to Pangolin.

## Problem Statement

Pangolin doesn't support wildcard domain forwarding, requiring manual resource creation for each Traefik service you may want to expose via Pangolin.

## Solution

This service:

1. Discovers routes from multiple Traefik instances matching configured domain whitelists
2. Creates corresponding HTTP resources in Pangolin
3. Creates (optional) static forwards for TCP/UDP services (that aren't configured in Traefik)

## Architecture

```
For each configured Traefik instance, the service discovers HTTP routes
and creates matching Pangolin resources within a designated site.
Each resource gets a target that routes traffic back to the originating
Traefik instance.

┌─────────────┐    API     ┌──────────────────┐    API     ┌─────────────┐
│   Traefik   │──────────► │ Sync Service     │──────────► │  Pangolin   │
│ Instance(s) │            │                  │            │  Service    │
└─────────────┘            └──────────────────┘            └─────────────┘
       │                            │                            │
       │ Routes:                    │ Creates:                   │ Tunnels:
       │ • app.example.com          │ • HTTP Resources           │ • app.example.com
       │ • api.example.com          │ • TCP/UDP Forwards         │ • api.example.com
       │ • *.mydomain.net           │ • Target configurations    │ • *.mydomain.net
```

## Key Features

- Dynamic route discovery from multiple Traefik instances
- Per-instance domain whitelists
- Static HTTP, TCP, and UDP forwarding for non-Traefik resoures
- Docker containerized

## Configuration

Copy `settings.example.yml` to `settings.yml` and configure:

```yaml
# Traefik sites to monitor
traefik_sites:
  - site_name: my-site
    api_url: "http://traefik:8080/api"
    target_host: "traefik"
    target_port: 80
    host_whitelist:
      - "example.com"
      - "mydomain.net"

# Pangolin API credentials
pangolin_api_url: "https://api.pangolin.com/v1"
pangolin_api_key: "your-api-key"
pangolin_org_id: "your-org-id"

# Optional static forwards
static_http_forwards:
  - subdomain: "app"
    domain: "example.com"
    site_name: server01
    target_host: my-app
    target_port: 80

static_tcp_forwards:
  - name: app1
    site_name: server02
    source_port: 2022
    target_host: my-tcp-app
    target_port: 2022

static_udp_forwards:
  - name: app2
    site_name: server02
    source_port: 5170
    target_host: my-udp-app
    target_port: 5170
```

## Usage

### Docker Compose (Recommended)

```bash
docker-compose up -d
```

### Manual Python

```bash
pip install requests pyyaml
python main.py
```

### Scheduled Execution

The service runs periodically (e.g., via cron) to sync new routes as they're discovered by Traefik.

## How It Works

1. Loads existing Pangolin resources, domains, and sites into memory
2. Creates configured static HTTP/TCP/UDP forwards
3. For each configured Traefik instance:
   - Fetches HTTP routers from Traefik API
   - Filters routes by domain whitelist
   - Creates missing HTTP resources in Pangolin
   - Configures targets to point back to that Traefik instance

## Requirements

- Python 3.11+
- Access to Traefik API
- Valid Pangolin API key with the following permissions:

  Organization:
  - `List Organizations`
  - `List Organization Domains`
  
  Site:
  - `Get Site`
  - `List Sites`
  
  Resource:
  - `Create Resource`
  - `Delete Resource`
  - `Get Resource`
  - `List Resources`
  - `Update Resource`
  
  Target:
  - `Create Target`
  - `Get Target`
  - `List Targets`
  
  Resource Rule:
  - `Create Resource Rule`
  - `List Resource Rules`
  - `Update Resource Rule`

