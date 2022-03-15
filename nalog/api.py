import datetime
import io
import json
from pprint import pprint
from typing import List, Dict, Union, Any, Optional

import pycurl


class NalogAPI:
    def __init__(self, email: str, inn: str, password: str):
        self._inn = inn
        self._password = password
        self._device_id = email
        self._base_url = 'https://lknpd.nalog.ru/'
        self._status_url = 'https://lkfl2.nalog.ru/lkfl/login/'
        self._api_url = self._base_url + 'api/v1/'
        self._auth_url = 'auth/lkfl'
        self._sale_url = 'income'
        self._sales_url = 'incomes/csv'
        self._cancel_url = 'cancel'
        self._check_download = 'receipt'
        self._summary_url = 'incomes/summary'
        self._bonus_url = 'taxpayer/bonus'
        self._info_url = 'job/info'
        self._debts_url = 'taxpayer/debts'
        self._app_version = '1.0.0'
        self._source_type = 'WEB'
        self._user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'

        self._operation_keys = ['id', 'date', 'name', 'price', 'tax', 'status', 'partner']
        self._customer_keys = ['type', 'inn', 'name']

        self.check_lkfl2_nalog()

    def check_lkfl2_nalog(self):
        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self._user_agent)
        c.setopt(pycurl.URL, self._status_url)
        c.setopt(pycurl.SSL_VERIFYPEER, 0)
        buffer = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, buffer.write)

        c.perform()
        http_code = c.getinfo(pycurl.HTTP_CODE)
        c.close()

        if http_code == 503:
            raise ResponseError('Сервис временно недоступен по причине проведения технических работ. '
                                'Приносим свои извинения в связи с доставленными неудобствами.')

    @property
    def user(self) -> dict:
        params = json.dumps(
            {
                'username': self._inn,
                'password': self._password,
                'deviceInfo': {
                    'sourceDeviceId': self._device_id,
                    'sourceType': self._source_type,
                    'appVersion': self._app_version,
                    'metaDetails': {
                        'userAgent': self._user_agent
                    }
                }
            }
        )

        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self._user_agent)
        c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json'])
        c.setopt(pycurl.URL, self._api_url + self._auth_url)
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, params)
        b = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.SSL_VERIFYPEER, 0)

        c.perform()
        post_result = b.getvalue()
        if not post_result:
            raise ResponseError('Can\'t get response from FNS')

        obj_result = json.loads(post_result)

        token = obj_result.get('token')
        refresh_token = obj_result.get('refreshToken')

        if not all([token, refresh_token]):
            raise ResponseError('Can\'t get tokens from FNS (auth)')

        c.close()

        return obj_result

    def create_receipt(self, name: str, price: int, download=False,
                       date: Optional[datetime] = None, contact_phone: str = None,
                       display_name: str = None, inn: str = None,
                       income_type='FROM_INDIVIDUAL', payment_type='CASH',
                       ignore_max_total_income_restriction=False) -> str:
        user = self.user

        if not date:
            date = datetime.datetime.now()

        params = json.dumps(
            {
                'operationTime': str(date.astimezone().replace(microsecond=0).isoformat()),
                'requestTime': str(date.astimezone().replace(microsecond=0).isoformat()),
                'services': [
                    {
                        'name': name,
                        'amount': str(price),
                        'quantity': '1',
                    }
                ],
                'totalAmount': str(price),
                'client': {
                    'contactPhone': contact_phone,
                    'displayName': display_name,
                    'inn': inn,
                    'incomeType': income_type,
                },
                'paymentType': payment_type,
                'ignoreMaxTotalIncomeRestriction': str(ignore_max_total_income_restriction).lower()
            }
        )

        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self._user_agent)
        c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json', f'Authorization: Bearer {user.get("token")}'])
        c.setopt(pycurl.URL, self._api_url + self._sale_url)
        c.setopt(pycurl.FAILONERROR, 1)
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, params)
        b = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.SSL_VERIFYPEER, 0)

        c.perform()
        post_result = b.getvalue()
        if not post_result:
            raise ResponseError('Can\'t get response from FNS (sale)')

        obj_result = json.loads(post_result)
        approved_receipt_uuid = obj_result.get('approvedReceiptUuid')
        c.close()

        receipt_url = f"{self._api_url}{self._check_download}/{self._inn}/{approved_receipt_uuid}/print"

        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self._user_agent)
        c.setopt(pycurl.URL, receipt_url)
        c.setopt(pycurl.SSL_VERIFYPEER, 0)
        b = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)

        c.perform()
        post_result = b.getvalue()
        if not post_result:
            raise ResponseError('Can\'t get response from FNS (download check)')

        http_code = c.getinfo(pycurl.HTTP_CODE)
        c.close()

        if http_code == 200:
            if download:
                with open(f'чек_{approved_receipt_uuid}.jpg', 'wb') as f:
                    f.write(post_result)
            return approved_receipt_uuid
        else:
            raise ResponseError('Can\'t get response from FNS (download check)')

    def get_history(self, from_datetime=datetime.datetime.fromtimestamp(100000),
                    to_datetime=datetime.datetime.now(),
                    desc=True, hide_cancelled=False) -> List[Dict[str, Union[datetime.datetime, float, Dict[str, Any]]]]:
        user = self.user

        url = f'https://lknpd.nalog.ru/api/v1/incomes/csv?from={from_datetime.astimezone().replace(microsecond=0).isoformat().replace("+", "%2B")}' \
              f'&to={to_datetime.astimezone().replace(microsecond=0).isoformat().replace("+", "%2B")}' \
              f'&sortBy={"operation_time:desc" if desc else "operation_time:asc"}'

        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self._user_agent)
        c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json',
                                     'Authorization: Bearer ' + user.get(
                                         'token')])
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.FAILONERROR, 1)
        b = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.SSL_VERIFYPEER, 0)

        c.perform()
        post_result = b.getvalue()
        if not post_result:
            raise ResponseError('Can\'t get response from FNS (history)')

        c.close()

        history = list(map(lambda x: x.split(';'),
                           post_result.decode('utf8').splitlines()[1:]))

        operations = []
        for item in history:
            if hide_cancelled and item[6] == 'Аннулирован':
                continue

            operation = {
                'id': item[0],
                'date': datetime.datetime.strptime(item[1], '%d.%m.%Y'),
                'name': item[2].replace('\"', ''),
                'price': float(item[3].replace(',', '.')),
                'tax': float(item[4].replace(',', '.')),
                'status': item[6],
                'customer': {
                    'type': item[7],
                    'inn': item[8],
                    'name': item[9],
                },
                'partner': item[10]
            }
            operations.append(operation)

        return operations

    def get_today_history(self, desc=True, hide_cancelled=False) -> List[Dict[str, Union[datetime.datetime, float, Dict[str, Any]]]]:
        return self.get_history(from_datetime=datetime.datetime.combine(datetime.datetime.now().date(), datetime.time(0, 0)),
                                desc=desc, hide_cancelled=hide_cancelled)

    def get_week_history(self, desc=True, hide_cancelled=False) -> List[Dict[str, Union[datetime.datetime, float, Dict[str, Any]]]]:
        return self.get_history(from_datetime=datetime.datetime.combine((datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().weekday())).date(), datetime.time(0, 0)),
                                desc=desc, hide_cancelled=hide_cancelled)

    def get_month_history(self, desc=True, hide_cancelled=False) -> List[Dict[str, Union[datetime.datetime, float, Dict[str, Any]]]]:
        return self.get_history(from_datetime=datetime.datetime.combine((datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().day - 1)).date(), datetime.time(0, 0)),
                                desc=desc, hide_cancelled=hide_cancelled)

    def get_previous_day_history(self, desc=True, hide_cancelled=False) -> List[Dict[str, Union[datetime.datetime, float, Dict[str, Any]]]]:
        return self.get_history(from_datetime=datetime.datetime.combine((datetime.datetime.now() - datetime.timedelta(days=1)).date(), datetime.time(0, 0)),
                                to_datetime=datetime.datetime.combine(datetime.datetime.now().date(), datetime.time(0, 0)),
                                desc=desc, hide_cancelled=hide_cancelled)

    def get_previous_week_history(self, desc=True, hide_cancelled=False) -> List[Dict[str, Union[datetime.datetime, float, Dict[str, Any]]]]:
        return self.get_history(from_datetime=datetime.datetime.combine((datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().weekday() + 7)).date(), datetime.time(0, 0)),
                                to_datetime=datetime.datetime.combine((datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().weekday())).date(), datetime.time(0, 0)),
                                desc=desc, hide_cancelled=hide_cancelled)

    def get_previous_month_history(self, desc=True, hide_cancelled=False) -> List[Dict[str, Union[datetime.datetime, float, Dict[str, Any]]]]:
        previous_month_days = (datetime.date(datetime.datetime.now().year, datetime.datetime.now().month, 1) - datetime.date(datetime.datetime.now().year, datetime.datetime.now().month-1, 1)).days
        return self.get_history(from_datetime=datetime.datetime.combine((datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().day - 1 + previous_month_days)).date(), datetime.time(0, 0)),
                                to_datetime=datetime.datetime.combine((datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().day - 1)).date(), datetime.time(0, 0)),
                                desc=desc, hide_cancelled=hide_cancelled)

    @staticmethod
    def get_profit(history: List[Dict[str, Union[datetime.datetime, float, Dict[str, Any]]]]):
        return sum(map(lambda operation: operation['price'] if operation['status'] == 'Зарегистрирован' else 0, history))

    def cancel(self, receipt_id: str, comment='Чек сформирован ошибочно',
               date=datetime.datetime.now(), partner_code=None):
        user = self.user

        params = json.dumps(
            {
                'operationTime': str(date.astimezone().replace(microsecond=0).isoformat()),
                'requestTime': str(date.astimezone().replace(microsecond=0).isoformat()),
                'comment': comment,
                'receiptUuid': str(receipt_id),
                'partnerCode': partner_code,
            }
        )

        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self._user_agent)
        c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json',
                                     'Authorization: Bearer ' + user.get('token')])
        c.setopt(pycurl.URL, self._api_url + self._cancel_url)
        c.setopt(pycurl.FAILONERROR, 1)
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, params)
        b = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.SSL_VERIFYPEER, 0)

        c.perform()
        post_result = b.getvalue()
        if not post_result:
            raise ResponseError('Can\'t get response from FNS (sale)')

        obj_result = json.loads(post_result)
        return obj_result

    @property
    def today(self):
        user = self.user

        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self._user_agent)
        c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json',
                                     'Authorization: Bearer ' + user.get(
                                         'token')])
        c.setopt(pycurl.URL, self._api_url + self._summary_url)
        c.setopt(pycurl.FAILONERROR, 1)
        b = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.SSL_VERIFYPEER, 0)

        c.perform()
        post_result = b.getvalue()
        if not post_result:
            raise ResponseError('Can\'t get response from FNS (summary)')

        c.close()

        return json.loads(post_result)

    @property
    def bonus(self):
        user = self.user

        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self._user_agent)
        c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json',
                                     'Authorization: Bearer ' + user.get(
                                         'token')])
        c.setopt(pycurl.URL, self._api_url + self._bonus_url)
        c.setopt(pycurl.FAILONERROR, 1)
        b = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.SSL_VERIFYPEER, 0)

        c.perform()
        post_result = b.getvalue()
        if not post_result:
            raise ResponseError('Can\'t get response from FNS (bonus)')

        c.close()

        return json.loads(post_result)

    @property
    def info(self):
        user = self.user

        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self._user_agent)
        c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json',
                                     'Authorization: Bearer ' + user.get(
                                         'token')])
        c.setopt(pycurl.URL, self._api_url + self._info_url)
        c.setopt(pycurl.FAILONERROR, 1)
        b = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.SSL_VERIFYPEER, 0)

        c.perform()
        post_result = b.getvalue()
        if not post_result:
            raise ResponseError('Can\'t get response from FNS (info)')

        c.close()

        return json.loads(post_result)

    @property
    def debts(self):
        user = self.user

        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self._user_agent)
        c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json',
                                     'Authorization: Bearer ' + user.get(
                                         'token')])
        c.setopt(pycurl.URL, self._api_url + self._debts_url)
        c.setopt(pycurl.FAILONERROR, 1)
        b = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.SSL_VERIFYPEER, 0)

        c.perform()
        post_result = b.getvalue()
        if not post_result:
            raise ResponseError('Can\'t get response from FNS (debts)')

        c.close()

        return json.loads(post_result)

    def get_url(self, receipt_id: str):
        return f"{self._api_url}{self._check_download}/{self._inn}/{receipt_id}/print"


class ResponseError(Exception):
    pass
