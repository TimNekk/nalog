# Moy Nalog API

![PyPI](https://img.shields.io/pypi/v/nalog?color=orange) ![Python 3.6, 3.4, 3.8](https://img.shields.io/pypi/pyversions/nalog?color=blueviolet)

**club_house_api** - this module is a Python client library for Moy Nalog API

## Installation

Install the current version with [PyPI](https://pypi.org/project/nalog/):

```bash
pip install nalog
```

## Usage

You can generate a token for clubhouse by going to the account section and generating a new token

```python
from nalog import NalogAPI

api = NalogAPI(
  email="example@email.com",
  inn="123456789012",
  password="my_secret_password"
)

receipt_id = api.create_receipt(name="Flower pot", price=199)
url = api.get_url(receipt_id)

print(url)
```

## Contributing

Bug reports and/or pull requests are welcome


## License

The module is available as open source under the terms of the [Apache License, Version 2.0](https://opensource.org/licenses/Apache-2.0)