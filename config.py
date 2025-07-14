from typing import Dict, List, Any, Callable, Tuple
import json

# Single base template
BASE_TEMPLATE = """user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

http {{
        sendfile on;
        tcp_nopush on;
        types_hash_max_size 2048;
    
        include /etc/nginx/mime.types;
        default_type application/octet-stream;

        {tls_config}
        {error_config}
        {server_tokens}

        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;
}}

server {{
    listen 80;
    listen 443 ssl;

    ssl_certificate /etc/ssl/certs/wildcard.pem;
    ssl_certificate_key /etc/ssl/private/wildcard.key;  
{body_component}
}} """

class ConfigGenerator:
    def __init__(self):
        # Cache for generated configurations
        self._config_cache = {}
        self.global_headers = """
    DEFAULT;
    DEFAULT;
    DEFAULT
    """
        
        # Header configurations
        self.header_configs = {
            "001": """add_header Some headers "header values";""",       
           
        }
        
        # Component generators mapping
        self.body_component_generators = {
            "error_page": self._error_page_component,
        }
        
        # Hash to component mapping with parameters
        self.body_hash_map = {
            # Error pages
            "001": {"type": "error_page", "params": [404, "404"]},
           
        }
    
    def _error_page_component(self, code: int, page: str, header_hash) -> str:
        """Generate error page component."""
        header_config = self.header_configs.get(header_hash)
        return f""" 
    error_page {code} /{page}.html;

    location = /{page}.html {{
        {header_config}
        root /var/www/error-pages;
        internal;
    }}    
    {self.global_headers}
    location / {{
        {header_config}
        return {code};
    }}"""
       
    
    def generate_tls_config(self, tls_params: Dict[str, Any]) -> str:
        """Generate TLS configuration from parameters."""
        domain = tls_params.get('domain')
        ssl_protocols = tls_params.get('ssl_protocols', 'TLSv1.2 TLSv1.3')
        cipher_suite = tls_params.get('cipher_suite')
        hsts_enabled = tls_params.get('hsts_enabled', True)
        
        if not domain:
            raise ValueError("Domain is required for TLS configuration")
        
        tls_config = ""

        tls_config += f"""
        ssl_protocols {ssl_protocols};"""
        
        # Add cipher suite if specified
        if cipher_suite:
            tls_config += f"""
        ssl_ciphers {cipher_suite};
        ssl_prefer_server_ciphers on;"""
        else:
            tls_config += """
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA256;
        ssl_prefer_server_ciphers on;"""
        
        # Add HSTS if enabled
        if hsts_enabled:
            tls_config += """
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;"""
        
        return tls_config


    def generate_body_component(self, body_hash: str, header_hash):
        """Generate body component from hash."""
        config = self.body_hash_map.get(body_hash)
        if not config:
            raise ValueError(f"Unknown body hash: {body_hash}")
        
        generator = self.body_component_generators[config["type"]]
        errors = self.generate_error_codes(config["params"][0])    
        return generator(*config["params"], header_hash), errors


    def generate_error_codes(self, target_code):    
        error_codes = [400, 401, 403, 405, 500, 502, 503]
        other_codes = [code for code in error_codes if code != target_code]
        return f"error_page {', '.join(map(str, other_codes))} = return/{target_code}"
    
    
    def get_server_tokens(self, tls_params):
        return f"server_tokens on;" if tls_params["server tokens"] == True else f"server_tokens off;" 
    

    def generate_config(self, body_hash: str, header_hash: str, tls_params: Dict[str, Any]) -> str:
        """Generate complete nginx configuration."""        
        body_component, errors = self.generate_body_component(body_hash, header_hash)
        tls_config = self.generate_tls_config(tls_params)
        server_tokens = self.get_server_tokens(tls_params)
        
        return BASE_TEMPLATE.format(
            server_tokens=server_tokens,
            tls_config=tls_config,
            error_config=errors,
            body_component=body_component
        )
    

    def get_cached_config(self, body_hash: str, header_hash: str, tls_params: Dict[str, Any]) -> str:
        """Get configuration with caching."""
        cache_key = f"{body_hash}-{header_hash}-{json.dumps(tls_params, sort_keys=True)}"
        
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        config = self.generate_config(body_hash, header_hash, tls_params)
        self._config_cache[cache_key] = config
        return config
    

    def clear_cache(self):
        """Clear the configuration cache."""
        self._config_cache.clear()
    
    
    def add_body_component(self, body_hash: str, component_type: str, params: List[Any]):
        """Add a new body component mapping."""
        if component_type not in self.body_component_generators:
            raise ValueError(f"Unknown component type: {component_type}")
        
        self.body_hash_map[body_hash] = {
            "type": component_type,
            "params": params
        }


    def add_header_config(self, header_hash: str, config: str):
        """Add a new header configuration."""
        self.header_configs[header_hash] = config


if __name__ == "__main__":
    generator = ConfigGenerator()
    
    config1 = generator.generate_config(
        body_hash="001",  
        header_hash="001",  
        tls_params={
            "domain": "example.com",
            "ssl_protocols": "TLSv1.3",
            "hsts_enabled": True,
            "server tokens": True
        }
    )
    
    print(config1)
