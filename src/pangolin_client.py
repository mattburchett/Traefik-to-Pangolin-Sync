import requests
from typing import Dict, Optional
from models import HTTPForward, TCPForward, UDPForward
from settings import Settings


class Pangolin:
    def __init__(self, s: Settings) -> None:
        self.resource_cache = []
        self.domain_id_cache = {}
        self.site_id_cache = {}
        self.s = s
        self.headers = {
            'accept': '*/*',
            'Authorization': f'Bearer {s.pangolin_api_key}',
            'Content-Type': 'application/json'
        }

    def _build_resource_cache(self) -> None:
        url = f"{self.s.pangolin_api_url}/org/{self.s.pangolin_org_id}/resources"

        if not self.resource_cache:
            r = requests.get(url, headers=self.headers)
            if not self._check_response_success(r):
                return None

            data = r.json()
            self.resource_cache = data.get('data', {}).get('resources', [])
            print(f"Loaded {len(self.resource_cache)} resources into cache")

    def _build_domain_id_cache(self) -> None:
        url = f"{self.s.pangolin_api_url}/org/{self.s.pangolin_org_id}/domains"

        if not self.domain_id_cache:
            r = requests.get(url, headers=self.headers)
            if not self._check_response_success(r):
                return None

            data = r.json()
            self.domain_id_cache = {domain['baseDomain']: domain['domainId'] for domain in data.get('data', {}).get('domains', {})}
            print(f"Loaded {len(self.domain_id_cache)} domain<>domainID mappings into cache")
            if self.domain_id_cache:
                print("  [Domain]→ [Domain ID]")
                for domain, domain_id in self.domain_id_cache.items():
                    print(f"  {domain}→ {domain_id}")

    def _build_site_id_cache(self) -> None:
        url = f"{self.s.pangolin_api_url}/org/{self.s.pangolin_org_id}/sites"

        if not self.site_id_cache:
            r = requests.get(url, headers=self.headers)
            if not self._check_response_success(r):
                return None

            data = r.json()
            self.site_id_cache = {site['name']: site['siteId'] for site in data.get('data', {}).get('sites', {})}
            print(f"Loaded {len(self.site_id_cache)} siteName<>siteID mappings into cache")
            if self.site_id_cache:
                print("  [Site Name]→ [Site ID]")
                for site_name, site_id in self.site_id_cache.items():
                    print(f"  {site_name}→ {site_id}")

    def _check_response_success(self, r: requests.Response) -> Optional[requests.Response]:
        if r.status_code not in (200, 201):
            try:
                fail_message = r.json().get('message', 'Unknown Error')
                print(f"API Error: {r.status_code} - {fail_message}")
                return None
            except Exception as e:
                print(f"Generic HTTP Error: Request failure: {r.status_code}")
                return None

        data = r.json()
        if not data.get('success', False):
            print(f"API Error: {data.get('message', 'Unknown error')}")
            return None

        return r

    def get_site_id_for_site_name(self, site_name: str) -> Optional[int]:
        site_id = self.site_id_cache.get(site_name)
        if not site_id:
            print(f"Error: Unable to find siteId for site name {site_name} in cache")
        return site_id

    def check_domain_in_resource_cache(self, domain: str) -> bool:
        for d in self.resource_cache:
            if not d.get('fullDomain'):
                continue

            if d.get('fullDomain').lower() == domain.lower():
                return True

        return False

    def check_tcp_forward_in_resource_cache(self, tcp_port: int) -> bool:
        for r in self.resource_cache:
            if r.get('proxyPort') == tcp_port and r.get('protocol') == 'tcp':
                return True
        return False

    def check_udp_forward_in_resource_cache(self, udp_port: int) -> bool:
        for r in self.resource_cache:
            if r.get('proxyPort') == udp_port and r.get('protocol') == 'udp':
                return True
        return False

    def build_caches(self) -> None:
        self._build_resource_cache()
        self._build_domain_id_cache()
        self._build_site_id_cache()

    def create_pangolin_tcp_resource(self, tcp_forward: TCPForward) -> Optional[int]:
        site_id = self.get_site_id_for_site_name(tcp_forward.site_name)
        if not site_id:
            return

        payload = {
            "name": tcp_forward.name or f"TCP Port {str(tcp_forward.source_port)}",
            "siteId": site_id,
            "http": False,
            "protocol": "tcp",
            "proxyPort": tcp_forward.source_port
        }

        url = f"{self.s.pangolin_api_url}/org/{self.s.pangolin_org_id}/site/{site_id}/resource"
        response = requests.put(url, headers=self.headers, json=payload)
        if not self._check_response_success(response):
            return None

        data = response.json()
        return data.get('data', {}).get('resourceId')


    def create_pangolin_udp_resource(self, udp_forward: UDPForward) -> Optional[int]:
        site_id = self.get_site_id_for_site_name(udp_forward.site_name)
        if not site_id:
            return

        payload = {
            "name": udp_forward.name or f"UDP Port {str(udp_forward.source_port)}",
            "siteId": site_id,
            "http": False,
            "protocol": "udp",
            "proxyPort": udp_forward.source_port
        }

        url = f"{self.s.pangolin_api_url}/org/{self.s.pangolin_org_id}/site/{site_id}/resource"
        response = requests.put(url, headers=self.headers, json=payload)
        if not self._check_response_success(response):
            return None

        data = response.json()
        return data.get('data', {}).get('resourceId')

    def create_pangolin_http_resource(self, forward: HTTPForward) -> Optional[int]:
        domain_id = self.domain_id_cache.get(forward.domain)
        if not domain_id:
            print(f"Error: No domain ID mapping found for {forward.domain}. Have you configured Traefik to allow resources for this domain?")
            return

        site_id = self.get_site_id_for_site_name(forward.site_name)
        if not site_id:
            return

        payload = {
            "name": forward.fqdn,
            "subdomain": forward.subdomain,
            "siteId": site_id,
            "http": True,
            "protocol": "tcp",
            "domainId": domain_id
        }

        url = f"{self.s.pangolin_api_url}/org/{self.s.pangolin_org_id}/site/{site_id}/resource"
        response = requests.put(url, headers=self.headers, json=payload)
        if not self._check_response_success(response):
            return None

        data = response.json()
        return data.get('data', {}).get('resourceId')

    def disable_http_resource_sso(self, resource_id: int) -> bool:
        url = f"{self.s.pangolin_api_url}/resource/{resource_id}"
        payload = {
            "sso": False
        }

        response = requests.post(url, headers=self.headers, json=payload)
        if not self._check_response_success(response):
            return False

        return True

    def create_pangolin_http_target(self, resource_id: int, forward: HTTPForward) -> Optional[int]:
        url = f"{self.s.pangolin_api_url}/resource/{resource_id}/target"
        payload = {
            "ip": forward.target_host,
            "method": forward.target_method.value,
            "port": forward.target_port,
            "enabled": True
        }

        response = requests.put(url, headers=self.headers, json=payload)
        if not self._check_response_success(response):
            return None

        return response.json().get('data', {}).get('targetId')

    def create_pangolin_tcp_target(self, resource_id: int, forward: TCPForward) -> Optional[int]:
        url = f"{self.s.pangolin_api_url}/resource/{resource_id}/target"
        payload = {
            "ip": forward.target_host,
            "method": "TCP",
            "port": forward.target_port,
            "enabled": True
        }

        response = requests.put(url, headers=self.headers, json=payload)
        if not self._check_response_success(response):
            return None

        return response.json().get('data', {}).get('targetId')

    def create_pangolin_udp_target(self, resource_id: int, forward: UDPForward) -> Optional[int]:
        url = f"{self.s.pangolin_api_url}/resource/{resource_id}/target"
        payload = {
            "ip": forward.target_host,
            "method": "UDP",
            "port": forward.target_port,
            "enabled": True
        }

        response = requests.put(url, headers=self.headers, json=payload)
        if not self._check_response_success(response):
            return None

        return response.json().get('data', {}).get('targetId')
