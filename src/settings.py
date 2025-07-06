import yaml
from pathlib import Path
from typing import Dict, List, Any
from models import HTTPForwardMethod, TraefikSite


class Settings:
    def __init__(self, yaml_path: str = None):
        # Define expected attributes with type hints
        self.pangolin_api_key: str
        self.pangolin_api_url: str
        self.pangolin_org_id: str
        self.traefik_sites: List[TraefikSite]
        self.static_http_forwards: List[Dict[str, Any]]
        self.static_tcp_forwards: List[Dict[str, Any]]
        self.static_udp_forwards: List[Dict[str, Any]]

        if yaml_path is None:
            yaml_path = Path(__file__).parent / 'settings.yml'

        try:
            with open(yaml_path, 'r') as file:
                data = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Settings file not found: {yaml_path}")
        except Exception as e:
            raise Exception(f"Error loading settings from {yaml_path}: {e}")

        for key, value in data.items():
            setattr(self, key, value)

        self.static_http_forwards = getattr(self, 'static_http_forwards') or []
        self.static_tcp_forwards = getattr(self, 'static_tcp_forwards') or []
        self.static_udp_forwards = getattr(self, 'static_udp_forwards') or []

        # Convert traefik_sites from dict to TraefikSite instances
        traefik_sites_raw = getattr(self, 'traefik_sites') or []
        self.traefik_sites = [
            TraefikSite(
                site_name=site['site_name'],
                api_url=site['api_url'],
                api_http_routers_path=site['api_http_routers_path'],
                target_host=site['target_host'],
                target_port=site['target_port'],
                target_method=HTTPForwardMethod(site['target_method'].upper()),
                host_whitelist=site.get('host_whitelist', [])
            )
            for site in traefik_sites_raw
        ]
