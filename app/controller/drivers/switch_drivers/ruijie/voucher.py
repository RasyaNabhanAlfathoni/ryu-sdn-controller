import requests


class RuijieVoucherManagementAPI:
    BASE_URL = "https://cloud-as.ruijienetworks.com"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def generate_voucher(
        self,
        group_id: int,
        quantity: int,
        profile: str,
        user_group_id: int,
        first_name: str = None,
        last_name: str = None,
        email: str = None,
        phone: str = None,
        comment: str = None
    ):
        url = f"{self.BASE_URL}/service/api/open/auth/voucher/create/{group_id}"
        params = {"access_token": self.access_token}

        payload = {
            "quantity": quantity,
            "profile": profile,
            "userGroupId": user_group_id
        }

        if first_name is not None:
            payload["firstName"] = first_name
        if last_name is not None:
            payload["lastName"] = last_name
        if email is not None:
            payload["email"] = email
        if phone is not None:
            payload["phone"] = phone
        if comment is not None:
            payload["comment"] = comment

        res = requests.post(
            url,
            params=params,
            json=payload,
            timeout=10
        )
        res.raise_for_status()
        return res.json()

    def list_vouchers(
        self,
        group_id: int,
        start: int = 0,
        page_size: int = 10
    ):
        url = f"{self.BASE_URL}/service/api/open/auth/voucher/getList/{group_id}"
        params = {
            "access_token": self.access_token,
            "start": start,
            "pageSize": page_size
        }

        res = requests.get(
            url,
            params=params,
            timeout=10
        )
        res.raise_for_status()
        return res.json()

    def create_custom_voucher(
        self,
        group_id: int,
        code: str,
        profile: str,
        user_group_id: int
    ):
        url = f"{self.BASE_URL}/service/api/open/auth/voucher/customerCreate/{group_id}/{code}"
        params = {"access_token": self.access_token}

        payload = {
            "groupId": str(group_id),
            "profile": profile,
            "userGroupId": user_group_id
        }

        res = requests.post(
            url,
            params=params,
            json=payload,
            timeout=10
        )
        res.raise_for_status()
        return res.json()