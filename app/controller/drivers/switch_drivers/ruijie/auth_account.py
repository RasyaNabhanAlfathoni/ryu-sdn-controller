import requests


class RuijieAuthAccountManagementAPI:
    BASE_URL = "https://cloud-as.ruijienetworks.com"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def create_account(
        self,
        group_id: int,
        username: str,
        password: str,
        profile_id: str,
        user_group_id: int,
        vpn_enable: bool = False,
        comment: str = None
    ):
        url = f"{self.BASE_URL}/service/api/open/auth/account/create/{group_id}"
        params = {"access_token": self.access_token}

        payload = {
            "username": username,
            "password": password,
            "profileId": profile_id,
            "userGroupId": user_group_id,
            "vpnEnable": vpn_enable
        }

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

    def delete_account(
        self,
        group_id: int,
        names: list
    ):
        url = f"{self.BASE_URL}/service/api/open/auth/account/delete/{group_id}"
        params = {"access_token": self.access_token}

        res = requests.delete(
            url,
            params=params,
            json=names,
            timeout=10
        )
        res.raise_for_status()
        return res.json()

    def list_accounts(
        self,
        group_id: int,
        start: int = 0,
        page_size: int = 10,
        name: str = None,
        status: str = None
    ):
        url = f"{self.BASE_URL}/service/api/open/auth/account/getList/{group_id}"
        params = {
            "access_token": self.access_token,
            "start": start,
            "pageSize": page_size
        }

        if name is not None:
            params["name"] = name
        if status is not None:
            params["status"] = status

        res = requests.get(
            url,
            params=params,
            timeout=10
        )
        res.raise_for_status()
        return res.json()

    def update_account(
        self,
        group_id: int,
        uuid: str,
        password: str,
        user_group_id: int
    ):
        url = f"{self.BASE_URL}/service/api/open/auth/account/update/{group_id}"
        params = {"access_token": self.access_token}

        payload = {
            "uuid": uuid,
            "password": password,
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

    def reset_account(
        self,
        group_id: int,
        names: list
    ):
        url = f"{self.BASE_URL}/service/api/open/auth/account/reset/{group_id}"
        params = {"access_token": self.access_token}

        res = requests.post(
            url,
            params=params,
            json=names,
            timeout=10
        )
        res.raise_for_status()
        return res.json()

    def get_account_summary(self, group_id: int):
        url = f"{self.BASE_URL}/service/api/open/auth/account/getStatusSummary/{group_id}"
        params = {"access_token": self.access_token}

        res = requests.get(
            url,
            params=params,
            timeout=10
        )
        res.raise_for_status()
        return res.json()
    
    def list_register_accounts(
            self,
            group_id: int,
            page: int,
            size: int,
            account: str = None
        ):
            url = f"{self.BASE_URL}/service/api/open/auth/register/getList/{group_id}"

            params = {
                "access_token": self.access_token,
                "page": page,
                "size": size
            }

            if account is not None:
                params["account"] = account

            res = requests.get(
                url,
                params=params,
                timeout=10
            )
            res.raise_for_status()
            return res.json()
