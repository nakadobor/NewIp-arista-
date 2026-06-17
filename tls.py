import ssl
import asyncio
import hashlib
import json

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def cert_meta(cert_bin, cert):
    try:
        sha256 = hashlib.sha256(cert_bin).hexdigest()
    except:
        sha256 = ""
    issuer = ""
    expire = ""
    try:
        issuer = dict(x[0] for x in cert["issuer"]).get("organizationName", "")
    except:
        pass
    try:
        expire = cert.get("notAfter", "")
    except:
        pass
    return {
        "issuer": issuer,
        "expire": expire,
        "sha256": sha256
    }

async def tls_check_async(ip, port, timeout=1.5):
    cfg = load_config()
    sni_hosts = cfg.get("sni_hosts", ["cloudflare.com"])
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_alpn_protocols(["h2", "http/1.1"])
    except:
        pass

    for sni in sni_hosts[:2]:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port, ssl=ctx, server_hostname=sni),
                timeout=timeout
            )
            
            ssl_obj = writer.get_extra_info("ssl_object")
            cert = ssl_obj.getpeercert()
            cert_bin = ssl_obj.getpeercert(binary_form=True)
            meta = cert_meta(cert_bin, cert)
            
            writer.close()
            await writer.wait_closed()
            
            return True, {
                "cert": cert,
                "meta": meta,
                "alpn": ssl_obj.selected_alpn_protocol() or "",
                "sni": sni
            }
        except:
            continue
    
    return False, None

def tls_check(ip, port, timeout=3):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(tls_check_async(ip, port, min(timeout, 1.5)))
        loop.close()
        return result
    except:
        return False, None
