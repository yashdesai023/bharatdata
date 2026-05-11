import ssl, sys, os
hosts = ["censusindia.gov.in"]
bundle = r"E:\\Private\\BharatData\\bharatdata\\data\\raw\\certs\\local_trust_bundle.pem"
for host in hosts:
    try:
        cert = ssl.get_server_certificate((host, 443))
    except Exception as e:
        print("bootstrap error for", host, e)
        continue
    with open(bundle, "r", encoding="utf8") as f:
        existing = f.read()
    if cert.strip() in existing:
        print(host, "cert already present")
        continue
    with open(bundle, "a", encoding="utf8") as f:
        f.write("\n\n# bootstrap {}\n".format(host))
        f.write(cert)
    print("Appended cert for", host)
