<div align="center">
<img src="https://socialify.git.ci/TimNekk/nalog/image?description=1&forks=1&issues=1&language=1&logo=https%3A%2F%2Fstatic.tildacdn.com%2Ftild3538-3137-4233-b035-306537633465%2F_.png&owner=1&pulls=1&stargazers=1" alt="nalog" width="640" height="320" />
</div>

# Moy Nalog API

![PyPI](https://img.shields.io/pypi/v/nalog?color=orange) ![Python 3.6, 3.4, 3.8](https://img.shields.io/pypi/pyversions/nalog?color=blueviolet)

**nalog** - this module is a Python client library for Moy Nalog API

## Installation

Install the current version with [PyPI](https://pypi.org/project/nalog/):

```bash
pip install nalog
```

## Usage

You need next data from [lkfl2.nalog.ru](https://lkfl2.nalog.ru/lkfl/login) to autharize:
- Email
- INN (Taxpayer Identification Number)
- Password

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
