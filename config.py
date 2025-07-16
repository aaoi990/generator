headers_to_dict = lambda h: {'status': h[0], **{k.strip(): v.strip() 
                            for item in h[1:] for k, v in [item.split(':', 1)] if ':' in item}}

headers_dict = headers_to_dict(headers_list)

 params={
            "domain": "example.com",
            "ssl_protocols": "TLSv1.3",
            "hsts_enabled": True,
            "server tokens": True,
            "normalised": "37872hdd",
            "headers": headers_dict  # Add the headers dict here
        }

def normalize_headers_hash(self, headers_dict: dict) -> str:
        """Generate normalized hash from headers dict (excluding status line)."""
        # Create string from headers only (not status line)
        headers_only = {k: v for k, v in headers_dict.items() if k != 'status_line'}
        headers_str = '\n'.join(f"{k}: {v}" for k, v in headers_only.items())
        return str(mmh3.hash(headers_str))
    
    def generate_config(self, body_hash: str, header_hash: str, tls_params: dict) -> str:
        """Generate config, normalizing headers internally."""
        # Extract headers from params
        headers_dict = tls_params.get('headers', {})
        
        # Normalize internally
        normalized_hash = self.normalize_headers_hash(headers_dict)
        
        # Use normalized hash for template lookup
        body_component, errors = self.generate_body_component(body_hash, normalized_hash)

