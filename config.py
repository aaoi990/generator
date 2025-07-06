from abc import ABC, abstractmethod
from pathlib import Path

class BaseConfig(ABC):
    """Base class with common nginx configuration template"""
    
    def __init__(self):
        self.default_port = 80
        self.default_ssl_port = 443
        self.enable_gzip = False
        self.enable_security_headers = False
        self.server_tokens = False
    
    @property
    @abstractmethod
    def config_type(self):
        """Return a string identifying the config type"""
        pass
    
    def generate(self, config_id, custom_data=None):
        """Main template method that builds the complete config"""       
        config_parts = []
        
        # Add upstream if needed
        error_handling = self.get_error_config()
        if error_handling:
            config_parts.append(error_handling)
        
        # Add main server block
        server_config = self.get_server_config(config_id, custom_data)
        config_parts.append(server_config)
        
        return "\n".join(config_parts)
    
    def get_error_config(self):
        """Override this if you need upstream configuration"""
        return None
    
    
    def get_server_config(self, config_id, custom_data):
        """Build the main server configuration"""
        server_tokens = self.get_server_tokens()
        server_name = self.get_server_name(config_id)
        listen_directive = self.get_listen_directive()
        ssl_config = self.get_ssl_config(config_id, custom_data)
        locations = self.get_location_blocks(config_id)
        common_directives = self.get_common_directives()
        
        config = f"""
{server_tokens}
        
server {{
    {listen_directive}
    server_name {server_name};
    
{ssl_config}
{common_directives}
{locations}
}}"""
        return config
    
    def get_server_name(self, config_id):
        """Get server name - can be overridden"""
        return f"{config_id}.internal.com"
    
    def get_server_tokens(self):
        """Get the server tokens"""        
        return f"server_tokens on;" if self.server_tokens else f"server_tokens off;" 
    
    def get_listen_directive(self):
        """Get listen directive - can be overridden"""
        return f"listen {self.default_port};"
    
    def get_ssl_config(self, config_id, custom_data):
        """Get SSL configuration if needed"""
        if self.default_port == 443:
            return f"""    ssl_certificate /etc/ssl/certs/{config_id}.crt;
    ssl_certificate_key /etc/ssl/private/{config_id}.key;
    
    {custom_data}"""
        #add the custom secure config here
        return ""
    
    def get_common_directives(self):
        """Common directives that most configs share"""
        directives = []
        
        if self.enable_gzip:
            directives.append("""    # Gzip compression
    gzip on;
    gzip_types text/css text/javascript application/javascript application/json;""")
        
        if self.enable_security_headers:
            directives.append("""    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";""")
        
        return "\n".join(directives)
    
    @abstractmethod
    def get_location_blocks(self, config_id):
        """Each config type must define its location blocks"""
        pass

class SecureConfig(BaseConfig):
    """API Server with minimal customization"""
    
    def __init__(self):
        super().__init__()
        self.default_port = 443  # Override to use SSL
    
    @property
    def config_type(self):
        return "404"
    
    def get_error_config(self):
        return f"""error handling"""
    
    def get_server_name(self, config_id):
        return f"api-{config_id}.internal.com"
    
    def get_location_blocks(self, config_id):
        return f"""    location /api/ {{
        proxy_pass http://api_backend_{config_id};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # API specific settings
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }}
    
    location /health {{
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }}"""

class SecureConfigExternal(SecureConfig):
    """API Server with minimal customization"""
    
    def __init__(self):
        super().__init__()
        self.server_tokens = True  
    

class StaticSiteConfig(BaseConfig):
    """Static site with just location customization"""
    
    @property
    def config_type(self):
        return "static_site"
    
    def get_server_name(self, config_id):
        return f"site-{config_id}.internal.com"
    
    def get_location_blocks(self, config_id):
        return f"""    root /var/www/{config_id};
    index index.html index.htm;
    
    location / {{
        try_files $uri $uri/ =404;
    }}
    
    location ~* \\.(css|js|png|jpg|jpeg|gif|ico|svg)$ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
    
    location = /favicon.ico {{
        log_not_found off;
        access_log off;
    }}"""

class DatabaseProxyConfig(BaseConfig):
    """Database proxy with SSL and custom timeouts"""
    
    def __init__(self):
        super().__init__()
        self.default_port = 443
        self.enable_gzip = False  # Disable gzip for database connections
    
    @property
    def config_type(self):
        return "database_proxy"
    
    def get_upstream_config(self, config_id):
        return f"""upstream db_backend_{config_id} {{
    server 10.0.2.10:5432;
    server 10.0.2.11:5432 backup;
}}"""
    
    def get_server_name(self, config_id):
        return f"db-{config_id}.internal.com"
    
    def get_location_blocks(self, config_id):
        return f"""    location / {{
        proxy_pass http://db_backend_{config_id};
        proxy_set_header Host $host;
        
        # Database specific settings
        proxy_read_timeout 600s;
        proxy_connect_timeout 10s;
        proxy_send_timeout 600s;
    }}"""

class NginxConfigGenerator:
    """Main generator class that manages all config types"""
    
    def __init__(self):
        self.configs = {}
        self.generated_configs = []
    
    def register_config(self, config_id, config_class):
        """Register a config class with IP lookup file"""
        if not issubclass(config_class, BaseConfig):
            raise TypeError("Config class must inherit from BaseConfig")
        
        self.configs[config_id] = config_class()
    
    def bulk_register(self, config_mapping):
        """Register multiple configs at once"""
        for config_id, config_class in config_mapping.items():
            self.register_config(config_id, config_class)
    
    def generate(self, config_id, jarm, body_hash, custom_data):
        """Generate co+nfig for a specific ID"""
        if config_id not in self.configs:
            raise ValueError(f"No config registered for ID: {config_id}")
        
        config_content = self.configs[config_id].generate(config_id, custom_data)
        config_type = self.configs[config_id].config_type        
        config = {
            'id': config_id,
            'type': config_type,
            'content': config_content,
            'jarm': jarm,
            'body_hash': body_hash,
            'extra_data': custom_data
        }  
        self.generated_configs.append(config)

    
    def save_configs(self, output_dir="nginx_configs"):
        """Save all generated configs to separate files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        for config in self.generated_configs:
            filename = f"BH:{config['id']}_JARM:{config['jarm']}_HH:{config['body_hash']}_{config['type']}.conf"
            filepath = output_path / filename
            
            with open(filepath, 'w') as f:
                f.write(config['content'])
            
            print(f"Saved: {filepath}")

