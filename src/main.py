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

    all_valid_domains = set()
    all_valid_tcp_ports = set()
    all_valid_udp_ports = set()

    static_domains, static_tcp_ports, static_udp_ports = sync.get_valid_resources(
        settings.static_http_forwards, settings.static_tcp_forwards, settings.static_udp_forwards
    )
    all_valid_domains.update(static_domains)
    all_valid_tcp_ports.update(static_tcp_ports)
    all_valid_udp_ports.update(static_udp_ports)

    for traefik_site in settings.traefik_sites:
        if not pangolin.get_site_id_for_site_name(traefik_site.site_name):
           continue

        print(f">>> Processing Traefik site: {traefik_site.site_name}")
        traefik = Traefik(settings, traefik_site)
        sync = Sync(settings, pangolin, traefik)
        sync.sync_traefik_hosts()

        traefik_domains, traefik_tcp_ports, traefik_udp_ports = sync.get_valid_resources(
            [], [], []
        )
        all_valid_domains.update(traefik_domains)
        all_valid_tcp_ports.update(traefik_tcp_ports)
        all_valid_udp_ports.update(traefik_udp_ports)

    if settings.cleanup_orphaned_resources:
        print(">>> Cleaning up orphaned resources...")
        pangolin.cleanup_orphaned_resources(all_valid_domains, all_valid_tcp_ports, all_valid_udp_ports)
    else:
        print(">>> Skipping cleanup of orphaned resources (disabled in settings)")

    print(">>> All syncs completed")

if __name__ == '__main__':
    main()
