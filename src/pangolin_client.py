import requests
from typing import Dict, Optional
from models import HTTPForward, TCPForward, UDPForward
from settings import Settings


class Pangolin:
    def __init__(self, s: Settings) -> None:
        self.resource_cache = []
        self.domain_id_cache = {}
        self.site_id_cache = {}
        self.site_nice_id_cache = {}
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
            sites = data.get('data', {}).get('sites', {})
            self.site_id_cache = {site['name']: site['siteId'] for site in sites}
            self.site_nice_id_cache = {site['niceId']: site['name'] for site in sites}
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

    def delete_resource(self, resource_id: int) -> bool:
        """Delete a resource from Pangolin"""
        url = f"{self.s.pangolin_api_url}/resource/{resource_id}"
        response = requests.delete(url, headers=self.headers)
        if not self._check_response_success(response):
            return False
        return True

    def get_resource_targets(self, resource_id: int) -> Optional[list]:
        """Get targets for a resource"""
        url = f"{self.s.pangolin_api_url}/resource/{resource_id}/targets"
        response = requests.get(url, headers=self.headers)
        if not self._check_response_success(response):
            return None
        
        data = response.json()
        return data.get('data', {}).get('targets', [])

    def _get_site_name_for_resource(self, resource: dict) -> str:
        """Get site name from resource using niceId lookup"""
        site_nice_id = resource.get('siteId')  # This is actually the niceId
        return self.site_nice_id_cache.get(site_nice_id, "unknown") if site_nice_id else "unknown"

    def _format_resource_info(self, resource: dict, site_name: str) -> str:
        """Format resource info string for logging"""
        resource_id = resource.get('resourceId')
        
        if resource.get('http', False):
            full_domain = resource.get('fullDomain', '').lower()
            targets = self.get_resource_targets(resource_id) if resource_id else []
            
            if targets and targets[0]:
                target = targets[0]
                target_host = target.get('ip', 'unknown')
                target_port = target.get('port', 'unknown')
                method = target.get('method', 'unknown').lower()
                return f"{full_domain}→ {method}://{target_host}:{target_port} ({site_name})"
            else:
                return f"{full_domain}→ unknown ({site_name})"
                
        elif resource.get('protocol') in ['tcp', 'udp']:
            protocol = resource.get('protocol').upper()
            proxy_port = resource.get('proxyPort')
            targets = self.get_resource_targets(resource_id) if resource_id else []
            
            if targets and targets[0]:
                target = targets[0]
                target_host = target.get('ip', 'unknown')
                target_port = target.get('port', 'unknown')
                return f"{protocol}:{proxy_port}→ {target_host}:{target_port} ({site_name})"
            else:
                return f"{protocol}:{proxy_port}→ unknown ({site_name})"
        
        return f"unknown resource ({site_name})"

    def _is_resource_orphaned(self, resource: dict, valid_domains: set, valid_tcp_ports: set, valid_udp_ports: set) -> bool:
        """Check if resource should be deleted as orphaned"""
        if resource.get('http', False):
            full_domain = resource.get('fullDomain', '').lower()
            return full_domain and full_domain not in valid_domains
            
        elif resource.get('protocol') == 'tcp':
            proxy_port = resource.get('proxyPort')
            return proxy_port and proxy_port not in valid_tcp_ports
            
        elif resource.get('protocol') == 'udp':
            proxy_port = resource.get('proxyPort')
            return proxy_port and proxy_port not in valid_udp_ports
            
        return False

    def cleanup_orphaned_resources(self, valid_domains: set, valid_tcp_ports: set, valid_udp_ports: set) -> None:
        """Remove resources from Pangolin that aren't in Traefik or static config"""
        if not self.resource_cache:
            print("No resources in cache to clean up")
            return

        orphaned_resources = []
        
        for resource in self.resource_cache:
            resource_id = resource.get('resourceId')
            if not resource_id:
                continue

            if self._is_resource_orphaned(resource, valid_domains, valid_tcp_ports, valid_udp_ports):
                site_name = self._get_site_name_for_resource(resource)
                resource_info = self._format_resource_info(resource, site_name)
                orphaned_resources.append((resource_id, resource_info))

        deleted_count = 0
        for resource_id, resource_info in orphaned_resources:
            print(f"[{resource_info}] Deleting orphaned resource...")
            if self.delete_resource(resource_id):
                deleted_count += 1
            else:
                print(f"[{resource_info}] Failed to delete resource")

        if deleted_count > 0:
            print(f"Deleted {deleted_count} orphaned resources")
            self.resource_cache = []
        else:
            print("No orphaned resources found")

    def update_target(self, target_id: int, ip: str, port: int, method: str, enabled: bool = True) -> bool:
        """Update an existing target"""
        url = f"{self.s.pangolin_api_url}/target/{target_id}"
        payload = {
            "ip": ip,
            "port": port,
            "method": method,
            "enabled": enabled
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        if not self._check_response_success(response):
            return False
        return True

    def delete_target(self, target_id: int) -> bool:
        """Delete a target"""
        url = f"{self.s.pangolin_api_url}/target/{target_id}"
        response = requests.delete(url, headers=self.headers)
        if not self._check_response_success(response):
            return False
        return True

    def _find_resource_by_http_domain(self, fqdn: str) -> Optional[dict]:
        """Find resource matching HTTP domain"""
        for resource in self.resource_cache:
            if (resource.get('http', False) and 
                resource.get('fullDomain', '').lower() == fqdn.lower()):
                return resource
        return None

    def _find_resource_by_tcp_port(self, port: int) -> Optional[dict]:
        """Find resource matching TCP port"""
        for resource in self.resource_cache:
            if (resource.get('protocol') == 'tcp' and 
                resource.get('proxyPort') == port):
                return resource
        return None

    def _find_resource_by_udp_port(self, port: int) -> Optional[dict]:
        """Find resource matching UDP port"""
        for resource in self.resource_cache:
            if (resource.get('protocol') == 'udp' and 
                resource.get('proxyPort') == port):
                return resource
        return None

    def _check_and_update_target(self, forward, resource: dict) -> bool:
        """Generic method to check and update resource targets"""
        resource_id = resource.get('resourceId')
        if not resource_id:
            return False
        
        targets = self.get_resource_targets(resource_id)
        if not targets:
            print(f"[{forward}] No targets found for existing resource")
            return False
        
        target = targets[0]
        target_id = target.get('targetId')
        needs_update = False
        
        # Check for differences
        if target.get('ip') != forward.target_host:
            print(f"[{forward}] Target host changed: {target.get('ip')} → {forward.target_host}")
            needs_update = True
        
        if target.get('port') != forward.target_port:
            print(f"[{forward}] Target port changed: {target.get('port')} → {forward.target_port}")
            needs_update = True
        
        # Check method for HTTP forwards
        if hasattr(forward, 'target_method'):
            if target.get('method') != forward.target_method.value:
                print(f"[{forward}] Target method changed: {target.get('method')} → {forward.target_method.value}")
                needs_update = True
        
        # Update if needed
        if needs_update:
            if not target_id:
                print(f"[{forward}] Cannot update - no target ID found")
                return False
            
            print(f"[{forward}] Updating existing resource configuration...")
            method = getattr(forward, 'target_method', None)
            method_value = method.value if method else getattr(forward, 'protocol', 'TCP').upper()
            return self.update_target(target_id, forward.target_host, forward.target_port, method_value)
        else:
            print(f"[{forward}] Configuration is up to date")
            return True

    def compare_and_update_http_resource(self, forward: HTTPForward) -> bool:
        """Compare HTTP resource configuration and update if needed"""
        resource = self._find_resource_by_http_domain(forward.fqdn)
        return self._check_and_update_target(forward, resource) if resource else False

    def compare_and_update_tcp_resource(self, forward: TCPForward) -> bool:
        """Compare TCP resource configuration and update if needed"""
        resource = self._find_resource_by_tcp_port(forward.source_port)
        if resource:
            # Add protocol info for method determination
            forward.protocol = 'tcp'
            return self._check_and_update_target(forward, resource)
        return False

    def compare_and_update_udp_resource(self, forward: UDPForward) -> bool:
        """Compare UDP resource configuration and update if needed"""
        resource = self._find_resource_by_udp_port(forward.source_port)
        if resource:
            # Add protocol info for method determination
            forward.protocol = 'udp'
            return self._check_and_update_target(forward, resource)
        return False

