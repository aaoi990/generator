
import numpy as np
import pandas as pd
from config import *


if __name__ == "__main__":
    data = [["25637482", "some html", "-1002489980", "HTTP/1.1 404 Not Found, Server: nginx, Date: , Content-Type: text/html, Content-Length: 548, Connection: keep-alive"]]
    config_mapping = {
        "25637482_-1002489980": SecureConfig,
        "647929283_-1692967738": StaticSiteConfig,
        "25637482_1982579955": DatabaseProxyConfig,
    }
    generator = NginxConfigGenerator()
    generator.bulk_register(config_mapping)

    for count, i in enumerate(data):
        try:
            generator.generate(f"{data[count][0]}_{data[count][2]}", 'tls',data[count][2], data)
        except:
            print(f"Cannot create config for:{data[count][0]}_{data[count][2]}")
     
    generator.save_configs()