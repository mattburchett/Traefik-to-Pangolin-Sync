from typing import Optional
from models import HTTPForward, TCPForward, UDPForward, HTTPForwardMethod, TraefikSite
from settings import Settings
from pangolin_client import Pangolin
from traefik_client import Traefik


class Sync:
    def __init__(self, s: Settings, p: Pangolin, t: Optional[Traefik] = None) -> None:
        self.s = s
        self.p = p
        self.t = t

    def _make_http_forward(self, forward: HTTPForward) -> None:
        print(f"[{forward}] Creating HTTP resource...")
        resource_id = self.p.create_pangolin_http_resource(forward)
        if not resource_id:
            print(f"[{forward}] Failed creating the resource")
            return

        print(f"[{forward}] Disabling SSO...")
        disable_sso_success = self.p.disable_http_resource_sso(resource_id)
        if not disable_sso_success:
            print(f"[{forward}] Failed disabling SSO for the resource")
            return

        print(f"[{forward}] Creating HTTP target...")
        target_id = self.p.create_pangolin_http_target(resource_id, forward)
        if not target_id:
            print(f"[{forward}] Failed creating target for the resource")
            return

    def _make_tcp_forward(self, forward: TCPForward) -> None:
        print(f"[{forward}] Creating TCP resource...")
        resource_id = self.p.create_pangolin_tcp_resource(forward)
        if not resource_id:
            print(f"[{forward}] Failed creating the resource")
            return

        print(f"[{forward}] Creating TCP target...")
        target_id = self.p.create_pangolin_tcp_target(resource_id, forward)
        if not target_id:
            print(f"[{forward}] Failed creating target for the resource")
            return

    def _make_udp_forward(self, forward: UDPForward) -> None:
        print(f"[{forward}] Creating UDP resource...")
        resource_id = self.p.create_pangolin_udp_resource(forward)
        if not resource_id:
            print(f"[{forward}] Failed creating the resource")
            return

        print(f"[{forward}] Creating UDP target...")
        target_id = self.p.create_pangolin_udp_target(resource_id, forward)
        if not target_id:
            print(f"[{forward}] Failed creating target for the resource")
            return

    def _build_httpforward_obj_from_dynamic(self, dynamic_http_forward_entry: str) -> Optional[HTTPForward]:
        parts = dynamic_http_forward_entry.split('.')
        domain = '.'.join(parts[-2:])
        subdomain = parts[0]

        return HTTPForward(subdomain=subdomain,
                           domain=domain,
                           site_name=self.t.site_name,
                           target_host=self.t.traefik_site.target_host,
                           target_port=self.t.traefik_site.target_port,
                           target_method=self.t.traefik_site.target_method)

    def _build_httpforward_obj_from_static(self, static_http_forward_entry: dict) -> Optional[HTTPForward]:
        # Use explicit site_name if provided in settings, otherwise fallback to domain mapping
        site_name = static_http_forward_entry.get('site_name')
        if not site_name:
            print(f"Error: Unable to create resource for {static_http_forward_entry['subdomain']}.{static_http_forward_entry['domain']}. No site_name provided")
            return

        return HTTPForward(subdomain=static_http_forward_entry['subdomain'],
                           domain=static_http_forward_entry['domain'],
                           site_name=site_name,
                           target_host=static_http_forward_entry['target_host'],
                           target_port=static_http_forward_entry['target_port'],
                           target_method=HTTPForwardMethod(static_http_forward_entry['target_method'].upper()))

    def _build_tcpforward_obj_from_static(self, static_tcp_forward_entry: dict) -> Optional[TCPForward]:
        return TCPForward(name=static_tcp_forward_entry.get('name', f"TCP Forward {static_tcp_forward_entry['source_port']}"),
                               site_name=static_tcp_forward_entry['site_name'],
                               source_port=static_tcp_forward_entry['source_port'],
                               target_host=static_tcp_forward_entry['target_host'],
                               target_port=static_tcp_forward_entry['target_port'])

    def _build_udpforward_obj_from_static(self, static_udp_forward_entry: dict) -> Optional[UDPForward]:
        return UDPForward(name=static_udp_forward_entry.get('name', f"UDP Forward {static_udp_forward_entry['source_port']}"),
                               site_name=static_udp_forward_entry['site_name'],
                               source_port=static_udp_forward_entry['source_port'],
                               target_host=static_udp_forward_entry['target_host'],
                               target_port=static_udp_forward_entry['target_port'])

    def _sync_dynamic_http_forwards(self) -> None:
        for dynamic_http_forward_entry in self.t.get_hosts():
            dynamic_http_forward = self._build_httpforward_obj_from_dynamic(dynamic_http_forward_entry)

            if not dynamic_http_forward:
                print(f"Error: Failed building HTTPForward object for Traefik host {dynamic_http_forward_entry}")
                continue

            if self.p.check_domain_in_resource_cache(dynamic_http_forward.fqdn):
                print(f"[{dynamic_http_forward}] Already in Pangolin. Skipping...")
                continue

            self._make_http_forward(dynamic_http_forward)

    def _sync_static_http_forwards(self, static_http_forwards: list) -> None:
        for static_http_forward_entry in static_http_forwards:
            static_http_forward = self._build_httpforward_obj_from_static(static_http_forward_entry)

            if not static_http_forward:
                fqdn = f"{static_http_forward_entry['subdomain']}.{static_http_forward_entry['domain']}"
                print(f"Error: Failed building HTTPForward object for static host {fqdn}")
                continue

            if self.p.check_domain_in_resource_cache(static_http_forward.fqdn):
                print(f"[{static_http_forward}] Already in Pangolin. Skipping...")
                continue

            self._make_http_forward(static_http_forward)

    def _sync_static_tcp_forwards(self, static_tcp_forwards: list) -> None:
        for static_tcp_forward_entry in static_tcp_forwards:
            static_tcp_forward = self._build_tcpforward_obj_from_static(static_tcp_forward_entry)

            if not static_tcp_forward:
                print(f"Error: Failed building TCPForward object for static port {static_tcp_forward_entry['source_port']}")
                continue

            if self.p.check_tcp_forward_in_resource_cache(static_tcp_forward.source_port):
                print(f"[{static_tcp_forward}] Already in Pangolin. Skipping...")
                continue

            self._make_tcp_forward(static_tcp_forward)

    def _sync_static_udp_forwards(self, static_udp_forwards: list) -> None:
        for static_udp_forward_entry in static_udp_forwards:
            static_udp_forward = self._build_udpforward_obj_from_static(static_udp_forward_entry)

            if not static_udp_forward:
                print(f"Error: Failed building UDPForward object for static port {static_udp_forward_entry['source_port']}")
                continue

            if self.p.check_udp_forward_in_resource_cache(static_udp_forward.source_port):
                print(f"[{static_udp_forward}] Already in Pangolin. Skipping...")
                continue

            self._make_udp_forward(static_udp_forward)

    def sync_traefik_hosts(self) -> None:
        """Sync hosts discovered from Traefik site"""
        if not self.t:
            print("Error: No Traefik client available for host discovery")
            return

        hosts = self.t.get_hosts()
        if not hosts:
            print(f"WARNING: No Traefik hosts found for site {self.t.site_name}")
            return

        print(f"\n>>> Creating HTTP Forwards (discovered from Traefik site: {self.t.site_name})...")
        self._sync_dynamic_http_forwards()

    def sync_static_forwards(self, static_http_forwards: list, static_tcp_forwards: list, static_udp_forwards: list) -> None:
        """Sync static forwards"""
        print("\n>>> Creating static HTTP Forwards...")
        self._sync_static_http_forwards(static_http_forwards)

        print("\n>>> Creating static TCP Forwards...")
        self._sync_static_tcp_forwards(static_tcp_forwards)

        print("\n>>> Creating static UDP Forwards...")
        self._sync_static_udp_forwards(static_udp_forwards)

    def get_valid_resources(self, static_http_forwards: list, static_tcp_forwards: list, static_udp_forwards: list) -> tuple:
        """Collect all valid domains and ports from Traefik and static config"""
        valid_domains = set()
        valid_tcp_ports = set()
        valid_udp_ports = set()

        if self.t:
            for dynamic_http_forward_entry in self.t.get_hosts():
                dynamic_http_forward = self._build_httpforward_obj_from_dynamic(dynamic_http_forward_entry)
                if dynamic_http_forward:
                    valid_domains.add(dynamic_http_forward.fqdn.lower())

        for static_http_forward_entry in static_http_forwards:
            static_http_forward = self._build_httpforward_obj_from_static(static_http_forward_entry)
            if static_http_forward:
                valid_domains.add(static_http_forward.fqdn.lower())

        for static_tcp_forward_entry in static_tcp_forwards:
            valid_tcp_ports.add(static_tcp_forward_entry['source_port'])

        for static_udp_forward_entry in static_udp_forwards:
            valid_udp_ports.add(static_udp_forward_entry['source_port'])

        return valid_domains, valid_tcp_ports, valid_udp_ports

