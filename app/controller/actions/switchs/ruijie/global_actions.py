from drivers.switch_drivers.ruijie.auto_discover import AutoDiscoverRuijie
from drivers.switch_drivers.ruijie.network_group import RuijieNetworkGroupsAPI
from drivers.switch_drivers.ruijie.voucher import RuijieVoucherManagementAPI
from drivers.switch_drivers.ruijie.auth_account import RuijieAuthAccountManagementAPI
from drivers.switch_drivers.ruijie.client_record import RuijieClientRecordAPI
from drivers.switch_drivers.ruijie.device_management import RuijieDeviceManagementAPI
from drivers.switch_drivers.ruijie.client_information import RuijieClientInformationAPI
from drivers.switch_drivers.ruijie.user_group import RuijieUserGroupManagementAPI
from drivers.switch_drivers.ruijie.wifi_management import RuijieWiFiManagementAPI
from drivers.switch_drivers.ruijie.traffic_statistics import RuijieTrafficStatisticsAPI

class RuijieSwitchGlobalActions:

    @staticmethod
    def get_actions(d):

        token = AutoDiscoverRuijie.ACCESS_TOKEN

        return {
            "list.network.group.ruijie": lambda p, logger: (
                RuijieNetworkGroupsAPI(token).list_groups()
            ),
            "add.network.group.ruijie": lambda p, logger: (
                RuijieNetworkGroupsAPI(token).create_group(
                    pGroupId=p["pGroupId"],
                    name=p["name"],
                    group_type=p["type"],
                    timezone=p.get("timezone"),
                    description=p.get("description"),
                    latitude=p.get("latitude"),
                    longitude=p.get("longitude"),
                    businessType=p.get("businessType")
                )
            ),
            "voucher.create.ruijie": lambda p, logger: (
                RuijieVoucherManagementAPI(token).generate_voucher(
                    group_id=p["group_id"],
                    quantity=p["quantity"],
                    profile=p["profile"],
                    user_group_id=p["userGroupId"],
                    first_name=p.get("firstName"),
                    last_name=p.get("lastName"),
                    email=p.get("email"),
                    phone=p.get("phone"),
                    comment=p.get("comment")
                )
            ),
            "voucher.list.ruijie": lambda p, logger: (
                RuijieVoucherManagementAPI(token).list_vouchers(
                    group_id=p["group_id"],
                    start=p.get("start", 0),
                    page_size=p.get("pageSize", 10)
                )
            ),
            "voucher.custom.ruijie": lambda p, logger: (
                RuijieVoucherManagementAPI(token).create_custom_voucher(
                    group_id=p["group_id"],
                    code=p["code"],
                    profile=p["profile"],
                    user_group_id=p["userGroupId"]
                )
            ),
            "account.create.ruijie": lambda p, logger: (
                RuijieAuthAccountManagementAPI(token).create_account(
                    group_id=p["group_id"],
                    username=p["username"],
                    password=p["password"],
                    profile_id=p["profileId"],
                    user_group_id=p["userGroupId"],
                    vpn_enable=p.get("vpnEnable", False),
                    comment=p.get("comment")
                )
            ),
            "account.delete.ruijie": lambda p, logger: (
                RuijieAuthAccountManagementAPI(token).delete_account(
                    group_id=p["group_id"],
                    names=p["names"]
                )
            ),
            "account.list.ruijie": lambda p, logger: (
                RuijieAuthAccountManagementAPI(token).list_accounts(
                    group_id=p["group_id"],
                    start=p.get("start", 0),
                    page_size=p.get("pageSize", 10),
                    name=p.get("name"),
                    status=p.get("status")
                )
            ),
            "account.update.ruijie": lambda p, logger: (
                RuijieAuthAccountManagementAPI(token).update_account(
                    group_id=p["group_id"],
                    uuid=p["uuid"],
                    password=p["password"],
                    user_group_id=p["userGroupId"]
                )
            ),
            "account.reset.ruijie": lambda p, logger: (
                RuijieAuthAccountManagementAPI(token).reset_account(
                    group_id=p["group_id"],
                    names=p["names"]
                )
            ),
            "account.summary.ruijie": lambda p, logger: (
                RuijieAuthAccountManagementAPI(token).get_account_summary(
                    group_id=p["group_id"]
                )
            ),
            "register.account.list.ruijie": lambda p, logger: (
                RuijieAuthAccountManagementAPI(token).list_register_accounts(
                    group_id=p["group_id"],
                    page=p.get("page", 1),
                    size=p.get("size", 10),
                    account=p.get("account")
                )
            ),
            "client.online.ruijie": lambda p, logger: (
                RuijieClientRecordAPI(token).get_client_records(
                    group_id=p["group_id"],
                    page_size=p.get("pageSize", 10),
                    page_index=p.get("pageIndex", 0),
                    sta_type="currentUser",
                    mac=p.get("mac"),
                    ssid=p.get("ssid"),
                    sn=p.get("sn")
                )
            ),
            "client.history.ruijie": lambda p, logger: (
                RuijieClientRecordAPI(token).get_client_records(
                    group_id=p["group_id"],
                    page_size=p.get("pageSize", 10),
                    page_index=p.get("pageIndex", 0),
                    sta_type="onofflineUserHistory",
                    mac=p.get("mac"),
                    ssid=p.get("ssid"),
                    sn=p.get("sn")
                )
            ),
            "client.info.current.ruijie": lambda p, logger: (
                RuijieClientInformationAPI(token).get_current_clients(
                    group_id=p.get("group_id"),
                    page_index=p.get("page_index"),
                    page_size=p.get("page_size")
                )
            ),
            "user.group.list.ruijie": lambda p, logger: (
                RuijieUserGroupManagementAPI(token).list_user_groups(
                    group_id=p["group_id"],
                    page_index=p.get("pageIndex", 0),
                    page_size=p.get("pageSize", 20)
                )
            ),
            "wifi.upsert.ruijie": lambda p, logger: (
                RuijieWiFiManagementAPI(token).upsert_wifi(
                    group_id=p["groupId"],
                    wifi_grp_ssid=p.get("wifiGrpSsid", False),
                    ssid_id=p.get("ssidId"),
                    wireless_conf=p["wirelessConfEntity"]
                )
            ),
            "traffic.app.group.minute.ruijie": lambda p, logger: (
                RuijieTrafficStatisticsAPI(token).app_group_minute(
                    group_id=p["group_id"],
                    sn=p["sn"],
                    intf_name=p.get("intfName", "all"),
                    start_time=p["start_time"],
                    end_time=p["end_time"],
                    size=p.get("size", 100)
                )
            ),
            "traffic.app.group.day.ruijie": lambda p, logger: (
                RuijieTrafficStatisticsAPI(token).app_group_day(
                    group_id=p["group_id"],
                    sn=p["sn"],
                    intf_name=p.get("intfName", "all"),
                    start_time=p["start_time"],
                    end_time=p["end_time"],
                    size=p.get("size", 100)
                )
            ),
            "traffic.app.name.minute.ruijie": lambda p, logger: (
                RuijieTrafficStatisticsAPI(token).app_name_minute(
                    group_id=p["group_id"],
                    sn=p["sn"],
                    intf_name=p.get("intfName", "all"),
                    start_time=p["start_time"],
                    end_time=p["end_time"],
                    page_index=p.get("pageIndex", 1),
                    page_size=p.get("pageSize", 10)
                )
            ),
            "traffic.app.name.day.ruijie": lambda p, logger: (
                RuijieTrafficStatisticsAPI(token).app_name_day(
                    group_id=p["group_id"],
                    sn=p["sn"],
                    intf_name=p.get("intfName", "all"),
                    start_time=p["start_time"],
                    end_time=p["end_time"],
                    page_index=p.get("pageIndex", 1),
                    page_size=p.get("pageSize", 10)
                )
            ),
            "traffic.peak.trend.ruijie": lambda p, logger: (
                RuijieTrafficStatisticsAPI(token).peak_rate_trend(
                    sn=p["sn"],
                    intf_name=p.get("intf_name", "global"),
                    start_time=p["start_time"],
                    end_time=p["end_time"]
                )
            ),
        }