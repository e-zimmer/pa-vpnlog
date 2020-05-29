# pa-vpnlog
Palo Alto VPN log grabber

Grabs past 7 days of user logs for VPN connect/disconnect and outputs CSV of data

## Clone and setup

```bash
git clone https://github.com/e-zimmer/pa-vpnlog && cd pa-vpnlog
python3 -m venv env  
source env/bin/activate  
python -m pip install -r requirements.txt  
cp dotpaenv .paenv  
```

### Usage & Examples
`pavpnlog.py` gather client connection data
```
usage: pavpnlog.py [-h] [-v] [-d]

Select options.

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  verbose
  -d, --debug    debug
```
