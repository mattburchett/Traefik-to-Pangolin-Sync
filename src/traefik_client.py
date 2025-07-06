import requests
from settings import Settings
from models import TraefikSite


class Traefik:
    def __init__(self, s: Settings, traefik_site: TraefikSite) -> None:
        self.s = s
        self.traefik_site = traefik_site
        self.hosts = []

    @property
    def site_name(self):
        return self.traefik_site.site_name

    def _get_traefik_hosts_raw(self) -> list:
        response = requests.get(self.traefik_site.api_url + self.traefik_site.api_http_routers_path)
        if response.status_code != 200:
            print(f"Error fetching Traefik hosts: {response.status_code} - {response.text}")
            return []

        try:
            hosts_raw = response.json()
        except ValueError as e:
            print(f"Error parsing JSON response from Traefik: {e}")
            return []

        if not isinstance(hosts_raw, list):
            print("Unexpected format for Traefik hosts data. Expected a list.")
            return []

        return hosts_raw

    def _clean_traefik_hosts_raw(self, hosts_raw: list) -> list:
        filtered = [h['rule'] for h in hosts_raw if any(domain in h['rule'] for domain in self.traefik_site.host_whitelist)]
        trimmed = [t.split('`')[1] for t in filtered]
        return trimmed

    def _remove_duplicate_hosts(self, hosts: list) -> list:
        return list(set(hosts))

    def get_hosts(self) -> list:
        if not self.hosts:
            hosts_raw = self._get_traefik_hosts_raw()
            hosts_cleaned = self._clean_traefik_hosts_raw(hosts_raw)
            self.hosts = self._remove_duplicate_hosts(hosts_cleaned)
        return self.hosts
