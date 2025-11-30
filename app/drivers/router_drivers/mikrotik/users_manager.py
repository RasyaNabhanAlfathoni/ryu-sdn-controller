from routeros_api import RouterOsApiPool

class RouterOSUserManagerDriver:
    """
    Unified user/group/active-user manager driver.
    - core_driver pattern: constructor expects core_driver (RouterOSApiDriver instance)
      so caller can do: RouterOSUserManagerDriver(core_driver)
    - Policies are provided as a list (["local","ssh","read"]) and converted to "local,ssh,read"
    """

    name = "routerosapi_user_manager"

    def __init__(self, core_driver):
        self.core = core_driver
        self.dev = core_driver.dev

    def _api(self):
        pool = RouterOsApiPool(
            host=self.dev["ip"],
            username=self.dev["username"],
            password=self.dev["password"],
            plaintext_login=True
        )
        return pool, pool.get_api()

    # -------------------------
    # helpers
    # -------------------------
    def _policies_to_str(self, policies):
        # policies input can be list or comma-string; normalize to comma-string
        if policies is None:
            return None
        if isinstance(policies, (list, tuple)):
            return ",".join(policies)
        if isinstance(policies, str):
            return policies
        return str(policies)

    def _allowed_address_to_str(self, addr):
        if addr is None:
            return None
        if isinstance(addr, (list, tuple)):
            return ",".join(addr)
        return str(addr)

    def get_user(self, name):
        pool, api = self._api()
        try:
            users = api.get_resource('/user').get(name=name)
            if not users:
                return None
            return users[0]
        finally:
            pool.disconnect()

    def get_group(self, name):
        pool, api = self._api()
        try:
            groups = api.get_resource('/user/group').get(name=name)
            if not groups:
                return None
            return groups[0]
        finally:
            pool.disconnect()

    def user_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource('/user').get()
        finally:
            pool.disconnect()

    def user_edit(self, p, logger=print):
        """
        Edit user by name.
        Optional fields:
            - password
            - group
            - comment
            - address (list/string)
            - expired_password (bool)
        """
        pool, api = self._api()
        try:
            user = self.get_user(p["name"])
            if not user:
                logger(f"User {p['name']} not found")
                return

            update = {"id": user["id"]}

            if "password" in p:
                update["password"] = p["password"]
            if "group" in p:
                update["group"] = p["group"]
            if "comment" in p:
                update["comment"] = p["comment"]
            if "address" in p:
                update["address"] = self._allowed_address_to_str(p["address"])
            if "expired_password" in p:
                update["expired-password"] = "yes" if p["expired_password"] else "no"

            api.get_resource('/user').set(**update)

            logger(f"Edited user {p['name']}")
        finally:
            pool.disconnect()

    def user_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            user = self.get_user(p["name"])
            if not user:
                logger(f"User {p['name']} not found")
                return

            api.get_resource('/user').remove(id=user["id"])
            logger(f"Deleted user {p['name']}")
        finally:
            pool.disconnect()

    def user_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            user = self.get_user(p["name"])
            if not user:
                logger(f"User {p['name']} not found")
                return

            api.get_resource('/user').set(id=user["id"], disabled="yes")
            logger(f"Disabled user {p['name']}")
        finally:
            pool.disconnect()

    def user_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            user = self.get_user(p["name"])
            if not user:
                logger(f"User {p['name']} not found")
                return

            api.get_resource('/user').set(id=user["id"], disabled="no")
            logger(f"Enabled user {p['name']}")
        finally:
            pool.disconnect()

    def user_comment(self, p, logger=print):
        pool, api = self._api()
        try:
            user = self.get_user(p["name"])
            if not user:
                logger(f"User {p['name']} not found")
                return

            api.get_resource('/user').set(id=user["id"], comment=p["comment"])
            logger(f"Updated comment for user {p['name']}")
        finally:
            pool.disconnect()

    def group_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource('/user/group').get()
        finally:
            pool.disconnect()

    def group_add(self, p, logger=print):
        """
        p example:
         {
           "name":"monitor",
           "policies": ["local","ssh","read","winbox"],
           "skin": "default"   # optional - routeros uses 'skin' property
         }
        """
        pool, api = self._api()
        try:
            payload = {"name": p["name"]}
            if "policies" in p:
                payload["policy"] = self._policies_to_str(p["policies"])
            if "skin" in p:
                payload["skin"] = p["skin"]
            api.get_resource('/user/group').add(**payload)
            logger(f"Added group {p['name']}")
        finally:
            pool.disconnect()

    def group_edit(self, p, logger=print):
        """
        Edit group by name.
        Supports: rename, policies, skin.
        """
        pool, api = self._api()
        try:
            group = self.get_group(p["name"])
            if not group:
                logger(f"Group {p['name']} not found")
                return

            update = {"id": group["id"]}

            if "new_name" in p:
                update["name"] = p["new_name"]
            if "policies" in p:
                update["policy"] = self._policies_to_str(p["policies"])
            if "skin" in p:
                update["skin"] = p["skin"]

            api.get_resource('/user/group').set(**update)

            logger(f"Edited group {p.get('new_name', p['name'])}")
        finally:
            pool.disconnect()

    def group_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            group = self.get_group(p["name"])
            if not group:
                logger(f"Group {p['name']} not found")
                return

            api.get_resource('/user/group').remove(id=group["id"])
            logger(f"Deleted group {p['name']}")
        finally:
            pool.disconnect()

    def _parse_active_flag(self, entry):
        """
        Construct a compact flags string for active user entry.
        We try to guess useful markers:
         - W: winbox (via contains 'winbox')
         - S: ssh
         - R: romon
         - H: web (http)
         - A: has address
         - V: has 'via' (some method)
        """
        flags = ""
        via = entry.get("via", "") or ""
        address = entry.get("address", "") or ""

        if via:
            flags += "V"
            v = via.lower()
            if "winbox" in v:
                flags += "W"
            if "ssh" in v:
                flags += "S"
            if "romon" in v:
                flags += "R"
            if "www" in v or "http" in v or "webfig" in v:
                flags += "H"

        if address:
            flags += "A"

        return flags

    def active_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            data = api.get_resource('/user/active').get()
            out = []
            for e in data:
                e2 = e.copy()
                e2["flags_parsed"] = self._parse_active_flag(e)
                out.append(e2)
            return out
        finally:
            pool.disconnect()

    def active_logout(self, p, logger=print):
        """
        Logout active sessions of a user.
        Supports:
        - logout all: { "name": "admin" }
        - logout by address: { "name": "admin", "address": "10.10.10.10" }
        - logout by via: { "name": "admin", "via": "ssh" }
        - combo: { "name": "admin", "address": "10.10.10.10", "via": "winbox" }
        """
        pool, api = self._api()
        try:
            active = api.get_resource('/user/active').get()
            kicked = 0

            target_name = p["name"]
            target_addr = p.get("address")
            target_via  = p.get("via")

            for session in active:
                if session.get("name") != target_name:
                    continue

                if target_addr and session.get("address") != target_addr:
                    continue

                if target_via and session.get("via") != target_via:
                    continue

                sid = session["id"]

                # FIX: RouterOS v7 uses request-logout, not remove
                api.get_resource('/user/active').call("request-logout", {"id": sid})
                kicked += 1

            if kicked == 0:
                if target_addr or target_via:
                    logger(f"No sessions match filters for user {target_name}")
                else:
                    logger(f"No active sessions found for {target_name}")
            else:
                logger(f"Kicked {kicked} session(s) for user {target_name}")
        finally:
            pool.disconnect()