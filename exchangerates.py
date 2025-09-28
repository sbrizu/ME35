import network, time, urequests

SSID = "Tufts_Wireless"   # use hotspot/IoT SSID if campus has a portal

def wifi_connect():
    sta = network.WLAN(network.STA_IF)
    if not sta.isconnected():
        print("Connecting to Wi-Fi…")
        sta.active(True)
        sta.connect(SSID)            # open network: SSID only
        while not sta.isconnected():
            time.sleep(0.2)
    print("Wi-Fi:", sta.ifconfig())

wifi_connect()

URL = "https://open.er-api.com/v6/latest/USD"
print("Fetching:", URL)

try:
    r = urequests.get(URL)
    print("HTTP status:", r.status_code)
    if r.status_code == 200:
        j = r.json()
        # Basic sanity
        print("Result:", j.get("result"))
        print("Updated:", j.get("time_last_update_utc"))
        print("Base:", j.get("base_code"))

        rates = j.get("rates", {})
        # Print a few you care about (add/remove as you like)
        for code in ("EUR", "PYG", "ARS", "GBP", "JPY", "BRL"):
            if code in rates:
                print(f"1 USD = {rates[code]} {code}")
            else:
                print(f"{code} not in response")
    else:
        print("Error body:", r.text[:200])
    r.close()
except Exception as e:
    print("Request failed:", e)
