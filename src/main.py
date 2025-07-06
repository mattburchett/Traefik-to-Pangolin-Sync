#!/usr/bin/env python3
from settings import Settings
from pangolin_client import Pangolin
from traefik_client import Traefik
from sync import Sync


def main():
    settings = Settings()
    pangolin = Pangolin(settings)
    sync = Sync(settings, pangolin)

    print(">>> Building Pangolin resource cache...")
    pangolin.build_caches()

    print(">>> Syncing static forwards...")
    sync.sync_static_forwards(static_http_forwards=settings.static_http_forwards,
                             static_tcp_forwards=settings.static_tcp_forwards,
                             static_udp_forwards=settings.static_udp_forwards)

    for traefik_site in settings.traefik_sites:
        if not pangolin.get_site_id_for_site_name(traefik_site.site_name):
           continue

        print(f">>> Processing Traefik site: {traefik_site.site_name}")
        traefik = Traefik(settings, traefik_site)
        sync = Sync(settings, pangolin, traefik)
        sync.sync_traefik_hosts()

    print(">>> All syncs completed")

if __name__ == '__main__':
    main()
